from app.integrations.base import SocialSourceAdapter
from app.integrations.official import discover, fetch_comments, IntegrationUnavailable


class ThreadsAdapter(SocialSourceAdapter):
    async def search(self, keywords, max_results=100):
        return await discover("THREADS", keywords, max_results)

    async def fetch_post(self, post_url_or_id):
        raise IntegrationUnavailable(
            "Use official keyword search or import a post JSON record"
        )

    async def fetch_comments(self, post_external_id):
        return await fetch_comments("THREADS", post_external_id)


threads_adapter = ThreadsAdapter()
