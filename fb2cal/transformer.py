from .facebook_user import FacebookUser

class Transformer:

    def transform_birthday_comet_monthly_to_birthdays(self, birthday_comet_root_json):
        """ Transforms outfrom from BirthdayCometMonthlyBirthdaysRefetchQuery to list of Birthdays """

        facebook_users = []

        for all_friends_by_birthday_month_edge in birthday_comet_root_json['data']['viewer']['all_friends_by_birthday_month']['edges']:
            for friend_edge in all_friends_by_birthday_month_edge['node']['friends']['edges']:
                friend = friend_edge['node']
                
                # Create Birthday object
                facebook_users.append(
                    FacebookUser(
                        friend["id"],
                        friend["name"],
                        friend["profile_url"],
                        friend["profile_picture"]["uri"],
                        friend["birthdate"]["day"],
                        friend["birthdate"]["month"],
                        friend["birthdate"]["year"]
                ))
                
        return facebook_users