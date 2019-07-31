# TravianBot
Travian bot for Czech servers.

This bot was originally created by user [Xezed](https://github.com/Xezed/travian_bot)

## Language dependecies

You need to change several things if you want this bot to work on servers with another language than Czech.

`authorization.py`
  * `18: 's1': 'Přihlásit+se'`
    * Check `POST` request from your browser when logging in to get correct value instead of `'Přihlásit+se'`
    
`check_adventure.py`
  * `50: hero_is_not_available = parser.find('img', {'alt': 'na cestě'})`
    * Change `na cestě` to sentence shown when your hero is on adventure. Depending on server language.
    
`credentials.py`
  * `3: SERVER_URL = 'https://ts3.czsk.travian.com/'`
    * This needs to be changed always to server URL you are playing on.
    
`builder.py`
  * `179: if parse_message == 'Nedostatek potravy: postavte nebo rozšiřte obilné pole':`
    * Value given when you don't have enough free crop for building available. Change this to message in your language.
  * `120: resources_amount = {'Dřevo': lumber, 'Hlina': clay,`
  
    `121:                     'Železo': iron, 'Obilí': crop}`  
      * Change `Dřevo, Hlina, Železo, Obilí` to resources in server language. 
      
`parse_village_fields.py`
* `27: minimal_resource = resource_name[:2]`
  * This might need to be changed, in Czech there needs to be compared only first 2 characters of resource name. In your language could be the comparison between resource name and resource field name different.
* ` 78: if (minimal_resource.lower() in field.lower()) and (10 >= fields_level < lowest_level):`
  * This is comparing resources and resource field names. There is not one way to do it, it can be different in every language.
