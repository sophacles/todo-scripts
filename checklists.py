# Checklist todo: add additional commands... e.g.
# list, add, remove, and so on

import json
import calendar
from datetime import datetime, date, timedelta
from operator import attrgetter
import argparse

from todo import Task, TodoFile, get_todo_env
import todo

# makes an easy hook for monkey-patch based testing
def get_today():
    return date.today()

def parse_day(day):
    try:
        day = int(day)
        return day
    except: #need to string parse
        day = day.lower().capitalize()
        try:
            return datetime.strptime(day, "%a").date().weekday()
        except:
            return datetime.strptime(day, "%A").date().weekday()


class ChecklistItem(object):
    def __init__(self, **kw):
        self.id = kw.get('id')
        self.text = kw.get('text','')

    def past_due(self, latest_task):
        raise NotImplemented("This is for subclasses silly")

    def shedule_next(self, latest_task):
        raise NotImplemented("This is for subclasses silly")

    def process(self, latest_task):
        new_task = Task(self.text, tags = {"checklist":self.id}, autodate=True)

        if latest_task is None:
            return new_task

        # task is not fully processed
        if not self.task_ended(latest_task):
            if not self.past_due(latest_task):
                return

            # if it isn't but it is done - process it ...
            if latest_task.done:
                status = latest_task.tags['checklist'].partition('_')[2]
                if not status:
                    latest_task.tags['checklist'] = "%s_%s" % (self.id, 'complete')
            #otherwise process it incomplete
            else:
                latest_task.do()
                latest_task.tags['checklist'] = "%s_%s" % (self.id, 'incomplete')

        # ... and schedule a new one
        # with scheduled checklist tasks - there can be only one, hence the
        # ended check above
        if self.schedule_next(latest_task):
            return new_task

    def toJSON(self):
        res = {}
        res['id'] = self.id
        res['text'] = self.text
        return res

    @staticmethod
    def task_ended(task):
        """ meaning is it properly proccessed through checklist - done and with
        a completion mark"""
        status = task.tags['checklist'].partition('_')[2]
        if task.done and (status == "complete" or status =="incomplete"):
            return True
        else:
            return False


class Daily(ChecklistItem):
    def __init__(self, **kw):
        super(Daily, self).__init__(**kw)

    def past_due(self, latest_task):
        today = get_today()
        if (today - latest_task.create).days >= 1:
            return True
        return False

    def schedule_next(self, latest_task):
        return self.past_due(latest_task)

    def toJSON(self):
        res =  super(Daily, self).toJSON()
        res['type'] = "daily"
        return res

class Weekly(ChecklistItem):
    def __init__(self, **kw):
        super(Weekly, self).__init__(**kw)
        self.day_of_week = parse_day(kw.get('day', 6)) #default to sunday

        # keep the math simple in sched -- never conflict
        self.complete_time = min(int(kw.get('complete_time', 1)), 7) - 1

    def past_due(self, latest_task):
        today = get_today()
        due = latest_task.create + timedelta(days=self.complete_time)
        if (today - due).days >= 1:
            return True
        else:
            return False

    def schedule_next(self, latest_task):
        today = get_today()
        if today.weekday() == self.day_of_week:
            return True
        return False

    def toJSON(self):
        res =  super(Weekly, self).toJSON()
        res['type'] = 'weekly'
        res['day'] = calendar.day_abbr[self.day_of_week].lower()
        res['complete_time'] = self.complete_time + 1
        return res

def add_months(sourcedate,months):
     month = sourcedate.month - 1 + months
     year = sourcedate.year + month / 12
     month = month % 12 + 1
     day = min(sourcedate.day,calendar.monthrange(year,month)[1])
     return date(year,month,day)

class Monthly(ChecklistItem):
    def __init__(self, **kw):
        super(Monthly, self).__init__(**kw)
        self.day_of_month = int(kw.get('day', 1))
        self.complete_time = int(kw.get('complete_time', 1)) - 1

    def past_due(self, latest_task):
        today = get_today()
        due = latest_task.create + timedelta(days=self.complete_time)
        if ((due.month +12) - latest_task.create.month) % 12 >=2:
            due = add_months(latest_task.create, 1)
        if (today - due).days >= 1:
            return True
        else:
            return False

    def schedule_next(self, latest_task):
        today = get_today()
        last_day_this_month = calendar.monthrange(today.year,today.month)[1]
        sched_day = min(self.day_of_month, last_day_this_month)
        if today.day == sched_day:
            return True
        else:
            return False

    def toJSON(self):
        res =  super(Monthly, self).toJSON()
        res['type'] = 'monthly'
        res['day'] = self.day_of_month
        res['complete_time'] = self.complete_time + 1
        return res


class Floating(ChecklistItem):
    def __init__(self, **kw):
        super(Floating, self).__init__(**kw)
        self.complete_time = int(kw.get('complete_time', 1)) - 1
        self.wait = int(kw.get("wait", 0))

    def past_due(self, latest_task):
        today = get_today()
        due = latest_task.create + timedelta(days=self.complete_time)
        if (today - due).days >= 1:
            return True
        return False

    def schedule_next(self, latest_task):
        today = get_today()
        if (today - latest_task.finish).days >= self.wait:
            return True
        return False

    def toJSON(self):
        res =  super(Floating, self).toJSON()
        res['type'] = 'floating'
        res['complete_time'] = self.complete_time + 1
        res['wait'] = self.wait
        return res

def parse_cl_items(s):
    """Take a json string of checklist items and make a dict of item objects keyed on
    item name (id)"""
    dispatch = {"floating":Floating,
                "weekly":Weekly,
                "monthly": Monthly,
                "daily":Daily
               }

    raw = json.loads(s)
    il = []
    for d in raw:
        t = d.pop('type')
        t = t.lower()
        il.append(dispatch[t](**d))

    items = dict()
    for cli in il:
        items[cli.id] = cli
    return items

def process_todos(todos, items):
    """given a list of all todos for consideration, make new ones as needed,
    properly mark finished and expired items, and generally handle checklist
    maintenance"""

    task_lists = {k:[] for k in items.keys()}
    for task in todos:
        if 'checklist' not in task.tags:
            continue
        clid, status = task.tags['checklist'].partition('_')[::2]
        task_lists[clid].append(task)

    new_tasks = []
    for tid, task_list in task_lists.iteritems():
        task_list.sort(key=attrgetter("create"))
        old_task = None
        if len(task_list):
            old_task = task_list[-1]
        new_task = items[tid].process(old_task)
        if new_task:
            new_tasks.append(new_task)
    return new_tasks

def serialize_cl_items(items):
    """Given a working dictionary of checklist items, turn them in to a json list
    of item dicts sutable for saving"""
    return json.dumps([x.toJSON() for x in items.values()])

def make_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", default="~/.todo.cfg",
            help="todo.sh config file to use")
    parser.add_argument("-d", "--date", default=None,
            help="process as for the given date instead of today")
    parser.add_argument("-f", "--file", default="checklist.json",
            help="The file containing checklist item configuration")
    return parser


def main():
    from os.path import join as J, isfile, isdir

    # handle command line
    parser = make_args()
    info = parser.parse_args()

    # get what we need from the todo config file - this allows for consistent handling
    todo.CONFIG_FILE = info.config_file
    tdir = get_todo_env("TODO_DIR")
    checklist_items = None
    # TODO: handle fake date

    with open(J(tdir, info.file), 'r') as item_file:
        checklist_items = parse_cl_items(item_file.read())

    # now for the fun part: open the todo.txt and done.txt files, then
    # combine them into one list for processing. this new list will not reorder
    # the files. Then, add the new items back to todo.txt. Any items marked done
    # by processing will not have been rearranged in order in the files, so when we
    # save each of the files, we have the processing info, and preserved order

    todos = TodoFile(J(tdir,"todo.txt"))
    todos.open()
    dones = TodoFile(J(tdir, "done.txt"))
    dones.open()

    all_todos = todos.tasks + dones.tasks
    new_items = process_todos(all_todos, checklist_items)
    todos.tasks.extend(new_items)
    todos.save()
    dones.save()
    return

if __name__=='__main__':
    main()

