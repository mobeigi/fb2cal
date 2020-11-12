from facebook_user import FacebookUser

class Transformer:

    def transform_birthday_comet_root_to_birthdays(self, birthday_comet_root_json):
        """ Transforms outfrom from BirthdayCometRootQuery to list of Birthdays """

        birthdays = []

        for all_friends_by_birthday_month_edge in birthday_comet_root_json['data']['viewer']['all_friends_by_birthday_month']['edges']:
            for friend_edge in all_friends_by_birthday_month_edge['node']['friends']['edges']:
                friend = friend_edge['node']

                # Create Birthday object
                birthdays.append(
                    FacebookUser(
                        friend["id"],
                        friend["name"],
                        friend["profile_url"],
                        friend["profile_picture"]["uri"],
                        friend["birthdate"]["day"],
                        friend["birthdate"]["month"]
                ))
                
        return birthdays