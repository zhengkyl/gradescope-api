import requests
from bs4 import BeautifulSoup
from enum import Enum
import sys
from dotenv import dotenv_values

try:
  from account import GSAccount
except ModuleNotFoundError:
  from .account import GSAccount

try:
  from course import GSCourse
except ModuleNotFoundError:
  from .course import GSCourse


class ConnState(Enum):
  INIT = 0
  LOGGED_IN = 1


class GSConnection():
  '''The main connection class that keeps state about the current connection.'''

  def __init__(self):
    '''Initialize the session for the connection.'''
    self.session = requests.Session()
    self.state = ConnState.INIT
    self.account = None

  def login(self, email, pswd):
    '''
    Login to gradescope using email and password.
    Note that the future commands depend on account privilages.
    '''
    init_resp = self.session.get("https://www.gradescope.com/")
    parsed_init_resp = BeautifulSoup(init_resp.text, 'html.parser')
    for form in parsed_init_resp.find_all('form'):
      if form.get("action") == "/login":
        for inp in form.find_all('input'):
          if inp.get('name') == "authenticity_token":
            auth_token = inp.get('value')

    login_data = {
        "utf8": "✓",
        "session[email]": email,
        "session[password]": pswd,
        "session[remember_me]": 0,
        "commit": "Log In",
        "session[remember_me_sso]": 0,
        "authenticity_token": auth_token,
    }
    login_resp = self.session.post(
        "https://www.gradescope.com/login", params=login_data)
    if len(login_resp.history) != 0:
      if login_resp.history[0].status_code == requests.codes.found:
        self.state = ConnState.LOGGED_IN
        self.account = GSAccount(email, self.session)
        return True
    else:
      return False

  def get_account(self):
    '''
    Gets and parses account data after login. Note will return false if we are not in a logged in state, but
    this is subject to change.
    '''
    if self.state != ConnState.LOGGED_IN:
      return False  # Should raise exception
    # Get account page and parse it using bs4
    account_resp = self.session.get("https://www.gradescope.com/")
    parsed_account_resp = BeautifulSoup(account_resp.text, 'html.parser')

    # Get instructor course data
    # instructor_courses = parsed_account_resp.find('h1', class_ ='pageHeading').next_sibling

    # for course in instructor_courses.find_all('a', class_ = 'courseBox'):
    #     shortname = course.find('h3', class_ = 'courseBox--shortname').text
    #     name = course.find('h4', class_ = 'courseBox--name').text
    #     cid = course.get("href").split("/")[-1]
    #     year = None
    #     print(cid, name, shortname)
    #     for tag in course.parent.previous_siblings:
    #         if 'courseList--term' in tag.get("class"):
    #             year = tag.string
    #             break
    #     if year is None:
    #         return False # Should probably raise an exception.
    #     self.account.add_class(cid, name, shortname, year, instructor = True)

    student_courses = parsed_account_resp.find(
        'h1', class_='pageHeading', string="Your Courses").next_sibling
    latest_term = student_courses.find(
        'div', class_='courseList--coursesForTerm')
    year = None
    for tag in latest_term.parent.previous_siblings:
      if tag.get("class") == "courseList--term pageSubheading":
        year = tag.body
        break

    course_list = latest_term.find_all('a')
    for course in course_list:
      shortname = course.find('h3', class_='courseBox--shortname').text
      name = course.find('h4', class_='courseBox--name').text
      cid = course.get("href").split("/")[-1]
      # print(shortname + " " + name)
      self.account.add_class(cid, name, shortname, year)

    # for course in student_courses.find_all('a', class_ = 'courseBox'):
    #     shortname = course.find('h3', class_ = 'courseBox--shortname').text
    #     name = course.find('h4', class_ = 'courseBox--name').text
    #     cid = course.get("href").split("/")[-1]

    #     for tag in course.parent.previous_siblings:
    #         if tag.get("class") == "courseList--term pageSubheading":
    #             year = tag.body
    #             break
    #     if year is None:
    #         return False # Should probably raise an exception.
    #     self.account.add_class(cid, name, shortname, year)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('missing argument: path to env file with email and password')
    sys.exit()
  env_path = sys.argv[1]
  config = dotenv_values(env_path)
  conn = GSConnection()
  conn.login(config["GRADESCOPE_EMAIL"], config["GRADESCOPE_PASSWORD"])
  print(conn.state)
  print()
  conn.get_account()

  for course in conn.account.student_courses.values():
    print(course.shortname + " " + course.name)
    course.get_student_assignments()
    print()
