from .facebook_user import FacebookUser

# Generates permalink to Facebook profile url
# This is needed in many cases as the vanity url may change over time
def generate_facebook_profile_url_permalink(facebook_user: FacebookUser):
    return f'https://www.facebook.com/{facebook_user.id}'
