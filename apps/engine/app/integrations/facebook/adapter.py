from app.integrations.base import SocialSourceAdapter
from app.integrations.official import discover, fetch_comments, IntegrationUnavailable


class FacebookAdapter(SocialSourceAdapter):
    async def search(self, keywords, max_results=100):
        return await discover("FACEBOOK", keywords, max_results)

    async def fetch_post(self, post_url_or_id):
        raise IntegrationUnavailable(
            "Read an authorized Page feed or import a post JSON record"
        )

    async def fetch_comments(self, post_external_id):
        return await fetch_comments("FACEBOOK", post_external_id)


facebook_adapter = FacebookAdapter()
