from .facebook_user import FacebookUser

# Generates permalink to Facebook profile url
# This is needed in many cases as the vanity url may change over time
def generate_facebook_profile_url_permalink(facebook_user: FacebookUser):
    return f'https://www.facebook.com/{facebook_user.id}'

# Facebook prepends an infinite while loop to their API responses as anti hijacking protection
# It must be stripped away before parsing a response as JSON
def remove_anti_hijacking_protection(text: str):
    return text.removeprefix("for (;;);")
