"""Official HTTP sources. Missing credentials are failures, never simulated success."""

import httpx
import asyncio
import re
from app.core.config import settings
from app.integrations.base import NormalizedSocialPost, NormalizedSocialComment
from app.infrastructure.security.vault import vault


class IntegrationUnavailable(RuntimeError):
    pass


async def discover(platform: str, keywords: list[str], max_results: int):
    token = vault.get_secret(f"{platform.lower()}_access_token")
    if not token:
        raise IntegrationUnavailable(
            f"{platform}: chưa cấu hình access token. Bạn có thể nhập JSON dữ liệu được phép truy cập."
        )
    results = []
    async with httpx.AsyncClient(timeout=25) as client:
        if platform == "THREADS":
            sources = [
                (
                    "https://graph.threads.net/keyword_search",
                    {
                        "q": keyword,
                        "search_type": "RECENT",
                        "fields": "id,text,permalink,username,timestamp",
                    },
                )
                for keyword in keywords
            ]
        elif platform == "FACEBOOK":
            if not settings.FACEBOOK_PAGE_IDS:
                raise IntegrationUnavailable(
                    "Facebook: cần SCANSOCIAL_FACEBOOK_PAGE_IDS và quyền đọc Page được cấp. Không hỗ trợ tìm kiếm tùy ý toàn Facebook."
                )
            sources = [
                (
                    f"https://graph.facebook.com/{settings.FACEBOOK_GRAPH_VERSION}/{page_id}/feed",
                    {"fields": "id,message,permalink_url,from,created_time"},
                )
                for page_id in settings.FACEBOOK_PAGE_IDS
            ]
        else:
            raise IntegrationUnavailable(
                "Live discovery supports FACEBOOK or THREADS; use JSON import for manual sources."
            )
        request_count = 0
        for source_index, (url, params) in enumerate(sources):
            after = None
            threshold = (
                max_results
                if source_index == len(sources) - 1
                else min(
                    max_results, len(results) + max(1, max_results // len(sources))
                )
            )
            while len(results) < threshold and request_count < 50:
                request_params = {
                    **params,
                    "limit": min(100, threshold - len(results)),
                }
                if after:
                    request_params["after"] = after
                response = await client.get(
                    url,
                    params=request_params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                request_count += 1
                if response.status_code != 200:
                    raise IntegrationUnavailable(
                        f"{platform}: API trả HTTP {response.status_code}; kiểm tra quyền và hạn mức."
                    )
                data = response.json()
                if data.get("error"):
                    raise IntegrationUnavailable(
                        f"{platform}: API từ chối yêu cầu; kiểm tra quyền access token."
                    )
                for item in data.get("data", []):
                    content = (
                        item.get("text")
                        if platform == "THREADS"
                        else item.get("message")
                    )
                    if not content:
                        continue
                    author = item.get("from", {})
                    username = item.get("username", "")
                    results.append(
                        NormalizedSocialPost(
                            platform=platform,
                            external_id=item["id"],
                            url=item.get("permalink")
                            or item.get("permalink_url")
                            or f"https://www.facebook.com/{item['id']}",
                            author_id=author.get("id"),
                            author_name=username or author.get("name", "Unknown"),
                            author_url=f"https://www.threads.net/@{username}"
                            if username
                            else None,
                            content=content,
                            posted_at=item.get("timestamp") or item["created_time"],
                        )
                    )
                next_after = data.get("paging", {}).get("cursors", {}).get("after")
                if (
                    not data.get("paging", {}).get("next")
                    or not next_after
                    or next_after == after
                ):
                    break
                after = next_after
                await asyncio.sleep(0.25)
    return results[:max_results]


async def fetch_comments(platform: str, post_id: str):
    token = vault.get_secret(f"{platform.lower()}_access_token")
    if not token:
        raise IntegrationUnavailable(f"{platform}: access token is not configured")
    if not re.fullmatch(r"[0-9_]{1,128}", post_id):
        raise IntegrationUnavailable(
            "An official numeric post ID is required for live comment synchronization"
        )
    if platform == "FACEBOOK":
        url = f"https://graph.facebook.com/{settings.FACEBOOK_GRAPH_VERSION}/{post_id}/comments"
        fields = "id,message,from,created_time"
    elif platform == "THREADS":
        url = f"https://graph.threads.net/{post_id}/replies"
        fields = "id,text,username,timestamp"
    else:
        raise IntegrationUnavailable(
            "Comment synchronization supports Facebook and Threads"
        )
    results, after = [], None
    async with httpx.AsyncClient(timeout=20) as client:
        for _ in range(10):
            params = {"fields": fields, "limit": 100}
            if after:
                params["after"] = after
            response = await client.get(
                url, params=params, headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200 or response.json().get("error"):
                raise IntegrationUnavailable(
                    f"{platform}: comment API rejected the request; verify permissions and rate limits"
                )
            body = response.json()
            for item in body.get("data", []):
                author = item.get("from", {})
                username = item.get("username")
                results.append(
                    NormalizedSocialComment(
                        external_id=item["id"],
                        author_name=username or author.get("name", "Unknown"),
                        author_id=author.get("id"),
                        author_url=f"https://www.threads.net/@{username}"
                        if username
                        else f"https://www.facebook.com/{author['id']}"
                        if author.get("id")
                        else None,
                        content=item.get("text") or item.get("message", ""),
                        posted_at=item.get("timestamp") or item.get("created_time"),
                    )
                )
            next_after = body.get("paging", {}).get("cursors", {}).get("after")
            if (
                not body.get("paging", {}).get("next")
                or not next_after
                or next_after == after
            ):
                break
            after = next_after
            await asyncio.sleep(0.25)
    return results
