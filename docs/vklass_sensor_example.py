# This file is here as an example reference on how to login and communicate with vklass. It is not used in the project
# This file relies on user/password login, which is not the case for most vklass users. There is no BankID support
# 

#!/usr/bin/python
# Vklass - school platform SE

# vklass.py
# scripts for command line sensor
# https://www.home-assistant.io/integrations/command_line/

# 
# version 20251110
# 

from datetime import datetime, timedelta
import requests, logging, json, re
import argparse

class Vklass(object):
    def __init__(self, username, password):
        """
        username = Username of account being logged in
        password = Password of account being logged in
        """
        self.username = username
        self.password = password

        self.cookies = {}
        self._login_page = "https://auth.vklass.se/credentials"
        self._login_page_signin = f"{self._login_page}/signin"
        self._base_custodian = "https://custodian.vklass.se"
        self._home = f"{self._base_custodian}/Home/Welcome"
        self._news = f"{self._base_custodian}/Home/News/"
        self._scoreboard = f"{self._base_custodian}/Account/Scoreboard?X-Requested-With=XMLHttpRequest"
        self._calendar = f"{self._base_custodian}/Events/FullCalendar"
    
    def login(self):
        # Get RequestVerificationToken
        request_validation_re = re.compile(r'<input name="__RequestVerificationToken" type="hidden" value="([^"]*)" />')
        
        logging.debug("Try get: " + self._login_page)
        response = requests.get(self._login_page, allow_redirects=True)
        logging.debug(f"Response code:{response.status_code}")
        if response.status_code != 200:
            logging.error('Could not fetch RequestVerificationToken from Vklass')
            exit(1)
        else:
            logging.debug('Save cookie in memory')
            self.cookies = response.cookies
            #logging.debug(response.cookies.get_dict())
            tokens = request_validation_re.findall(response.text)
        
        # Get se.vklass.authentication cookie
        logging.debug("Try get: " + self._login_page_signin)
        response = requests.post(self._login_page_signin,
                    data = {
                    "__RequestVerificationToken": tokens[0],
                    "Username": self.username,
                    "Password": self.password,
                    "RememberMe": "false"
                    },
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                    cookies=self.cookies, allow_redirects=False)
        #logging.debug(f"Response {response.text}")
        logging.debug(f"Response code:{response.status_code}")
        #logging.debug(f"Response headers {response.request.headers}")
        
        if response.status_code == 302:
            logging.debug('Save cookie in memory')
            self.cookies = response.cookies
            #logging.debug(response.cookies.get_dict())
            logging.info('Vklass logged in.')
            return True
        elif response.status_code == 200:
            logging.error('Could not log in to Vklass')
            logging.error('  Wrong username or password?')
            return False
        else:
            logging.error('Could not log in to Vklass')
            logging.error('  Connection problem?"')
            return False
            
    def get_scoreboard(self):
        logging.debug("Try get: " + self._scoreboard)
        response = requests.get(self._scoreboard, cookies=self.cookies,
            allow_redirects=False)
        if response.status_code != 200:
            logging.warning('Could not get content from Vklass scoreboard')
            return None
        else:
            try:
                #logging.info(response.text)
                json_response = json.loads(response.text)
                return json_response
            except ValueError:
                logging.warning(f"Could not decode json from {self._scoreboard}")
                return
    
    def get_home(self,):
        logging.debug("Try get: " + self._home)
        response = requests.get(self._home,
                    cookies=self.cookies, allow_redirects=False)
        
        if response.status_code != 200:
            logging.warning('Could not get content from Vklass home')
            return None
        else:
            try:
                request_validation_re = re.compile(r'<div class=\"vk-student-card\">([\s\S.]*?)(?:<\/div>\r\n\t\t\t\t\t\r\n\r\n|<\/div>\r\n\t\t\t<\/vkau-swipe>)')
                html_response = request_validation_re.findall(response.text)
                
                logging.info(f"Vklass number of children: {len(html_response)}")
                
                # Debug to html blob
                if False:
                    with open("vklass_html_blob.html", "w") as f:
                        f.write('/n/n'.join(html_response))
                #logging.debug(html_response)
                
                children = dict()
                childs = list()
                
                for index, item in enumerate(html_response):
                    item = item.replace("\r\n","")
                    item = item.replace("\t","")
                    
                    logging.debug(item)
                    name = re.findall(r'<h2.*>(.*?)<\/h2>', item)
                    img = re.findall(r'<vkau-icon-badge image-url="(.*?)"', item)
                    caretime = re.findall(r'<a class="vk-link" href="#\/CareSchedule\/Overview">.*?<span class="vk-link__text">(.*?)<\/span>', item)
                    check = re.findall(r'<div class="vk-flex vk-flex--v-align-center">.*<span class="text-bold">(.*?)<\/span>.*<\/div>', item)
                    food = re.findall(r'<div class="vk-student-card__day" (?:[^>]*)><h3>([^>]*)<\/h3>.*?(?=<ul)(.*?(?=<\/div>))', item)
                    id = re.findall(r'<a class="vk-link" href="#\/Calendar\/Schedule\?date=.*&amp;studentIds=(.*?)">', item)
                    
                    child = dict()
                    child["img"] = img[0]
                    if len(id) > 0:
                        child["id"] = int(id[0])
                    if len(caretime) > 0:
                        child["caretime"] = caretime[0].replace('&#x2013;','-').replace(' ','')
                    if len(check) > 0:
                        child["check"] = check[0]
                    
                    logging.debug(f"Food: {food}")
                    if len(food) > 0:
                        child["food"] = dict()
                        for food_day in food:
                            #logging.debug(f"Food: {food_day}")
                            food_day_item = list()
                            for food_day_item in food_day:
                                if '<ul>' in food_day_item:
                                    food_day_item = food_day_item.replace('&#xD;','').replace('<ul>','').replace('</ul>','').replace('<li>','').split('</li>')
                                    food_day_item = list(filter(None, food_day_item))
                                else:
                                    food_day_item_header = food_day_item

                            child["food"].update({food_day_item_header: food_day_item})
                            
                    child["calendar"] = dict()
                    children[name[0]] = child
                    childs.append(name[0])
                children.update({"childs": childs})
                
                return children
            except ValueError:
                logging.warning(f"Could not decode page from {self._home}")
                return
    
    def get_news(self,):
        logging.debug("Try get: " + self._news)
        response = requests.get(self._news,
                    cookies=self.cookies, allow_redirects=False)
        if response.status_code != 200:
            logging.warning('Could not get content from Vklass news')
            return None
        else:
            try:
                request_validation_re = re.compile(r'common/views/shared/display-templates/news-feed-model/news-feed-model\', \'(.*?)\', ')
                json_response = request_validation_re.findall(response.text)[0]
                #logging.info(json)
                news_data = json.loads(json_response)
                news_data_new = list()
                for index, news in enumerate(news_data['newsArticles']):
                    news_date = datetime.strptime(news['publishDate'], '%Y-%m-%d').date()
                    
                    if news_date > (datetime.today()-timedelta(days=3)).date():
                        new_news = dict()
                        for header in ['title','publishDate','authorName','introText','text','tags']:
                            new_news.update({header: news[header]})
                    
                        new_news["files"] = len(news["files"])
                        new_news["children"] = list()
                        for child in news["children"]:
                            new_news["children"].append(child["name"])
                    
                        news_data_new.append(new_news)
                    
                return news_data_new
            except ValueError:
                logging.warning(f"Could not decode json from {self._news}")
                return
    
    def get_calendar(self,student:int=None,start=None,end=None):
        logging.debug("Try get: " + self._calendar)
        data = {
                    "students": student,
                    "start": datetime.now().astimezone().replace(microsecond=0).isoformat(),
                    "end": (datetime.now()+timedelta(hours=24)).astimezone().replace(microsecond=0).isoformat(),
                    }
        #logging.debug(data)
        
        response = requests.post(self._calendar,
                    data = data,
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'text/html'
                        },
                    cookies=self.cookies, allow_redirects=False)
        
        #logging.debug(response.text)
        logging.debug(f"Response code: {response.status_code}")
        if response.status_code != 200:
            logging.warning('Could not get content from Vklass calendar')
            return None
        else:
            try:
                #logging.debug(response.text)
                calendar_data = json.loads(response.text)
                
                gymclass = list()
                next_class = None
                for index, event in enumerate(calendar_data):
                    new_event = dict()
                    logging.debug(f"")
                    
                    for header in ['title','text','start','end','eventType','className']:
                        logging.debug(f" {header}: {event[header]}")
                        if event[header]:
                            new_event.update({header: event[header]})
                        
                            if header == 'start' or header == 'end':
                                new_event.update({header: datetime.strptime(event[header], '%Y-%m-%d %H:%M').isoformat() })
                            
                #    if datetime.strptime(event['start'], '%Y-%m-%d %H:%M') > datetime.now() \
                #        and not next_class:
                #            next_class = event['start'][-5:] + " " +event['title']
                    
                    if event['text'].lower() == 'idh':
                        if datetime.today().strftime('%Y-%m-%d') in event['start']:
                          gymclass.append('today')
                        elif (datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d') in event['start']:
                          gymclass.append('tomorrow')
                    
                    calendar_data[index] = new_event
                    
                return calendar_data, gymclass, next_class
            except ValueError:
                logging.warning(f"Could not decode json from {self._calendar}")
                return


if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
  try:
    import testkeys2
    logging.getLogger().setLevel(logging.DEBUG)
    api = Vklass(testkeys.username, testkeys.password)
    
  except ImportError:
    logging.debug("No testkeys")
    try:
      parser = argparse.ArgumentParser()
      parser.add_argument("-u", "--username", required = True, help = "Username")
      parser.add_argument("-p", "--password", required = True, help = "Password")
      parser.add_argument("-l", "--loglevel", type=str, default="warning", help = "log level")
      args = parser.parse_args()

      levels = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG
      }
      log_level = levels.get(args.loglevel.lower())
      
      logging.getLogger().setLevel(log_level)
      logging.info(f"vklass username: {args.username}")
      api = Vklass(args.username, args.password)
    except argparse.ArgumentError:
      logging.error("No arguments!")
      exit(1)
       
      
  if api.login() != True:
        exit(1)
  else:
        data = dict()
        
        scoreboard = api.get_scoreboard()
        if scoreboard:
          data["scoreboard"] = scoreboard
        news = api.get_news()
        if news:
          data.update({"news": news})
          
        home = api.get_home()
        if home:
          data.update(home)
        
        for child in data['childs']:
          logging.debug(f"Child:{child} {data[child] }")
          if 'id' in data[child]:
              calendar, gymclass, next_class = api.get_calendar(student=data[child]['id'])
              data[child].update({"calendar": calendar})
              data[child].update({"gymclass": gymclass})
              data[child].update({"next_class": next_class})
        logging.info('Vklass dumping data as json')
        print(json.dumps(data, indent=4))