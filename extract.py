  
import json
  
# Opening JSON file
with open('sample.json', 'r') as openfile:
  
    # Reading from json file
    json_object = json.load(openfile)
  

# print(type(json_object))
user =[]
bot = []
for element in json_object:
    if element['event']=='user':
        user.append(element)
    if element['event']=='bot':
        bot.append(element)
print(bot)
print("Last bot response was:")
print(bot[-1])