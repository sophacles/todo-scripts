import os
from unittest import TestCase
from datetime import date, timedelta
import json

# Assume Task works - for the stuff needed mocks are the same code as Task
from todo import Task, TodoFile

import checklists
from checklists import ChecklistItem, Daily, Weekly, Monthly, Floating
from checklists import parse_cl_items, serialize_cl_items, process_todos, parse_day


# multiple inheritance mixin pattern - hate me if you want
class PastDuePasses(object):
    def past_due(self, *args):
        return True
class PastDueFails(object):
    def past_due(self, *args):
        return False

class SchedulePasses(object):
    def schedule_next(self, *args):
        return True
class ScheduleFails(object):
    def schedule_next(self, *args):
        return False

class TestChecklistItemCommon(TestCase):
    """use mocks to handle a simple recurring item, rather than conflating actual ones"""
    def setUp(self):
        self.test_id = "testitem"
        self.test_text = "a test checklist item"
        self.ended = Task(task=self.test_text)
        self.ended.tags={"checklist":"%s_complete" % (self.test_id,)}
        self.ended.do()
        self.half_ended_insane = Task(task=self.test_text)
        self.half_ended_insane.tags={"checklist":"%s_complete" % (self.test_id,)}
        self.half_ended = Task(task=self.test_text)
        self.half_ended.tags={"checklist":"%s" % (self.test_id,)}
        self.half_ended.do()
        self.active = Task(task=self.test_text)
        self.active.tags={"checklist":self.test_id}

    def test_task_ended(self):
        """Base: make sure the task_ended method works"""
        self.assertTrue(ChecklistItem.task_ended(self.ended))
        self.assertFalse(ChecklistItem.task_ended(self.half_ended_insane))
        self.assertFalse(ChecklistItem.task_ended(self.half_ended))
        self.assertFalse(ChecklistItem.task_ended(self.active))

    def test_process_no_history(self):
        """Base: ensure no history is OK"""
        i = ChecklistItem(id=self.test_id, text=self.test_text)
        t = i.process(None)
        self.assertEqual(t.tags['checklist'], self.test_id)
        self.assertEqual(t.task, self.test_text)
        self.assertEqual(t.create, date.today())

    def test_latest_task_active(self):
        """Base: don't do anything if item isn't past-due"""
        class TestItem(PastDueFails, SchedulePasses, ChecklistItem):
            pass
        i = TestItem(id=self.test_id, text=self.test_text)
        self.assertEqual(i.process(self.active), None)

    def test_ended_scheduling(self):
        """Base: test scheduling secanrios with properly ended task"""
        class TestItem(PastDuePasses, SchedulePasses, ChecklistItem):
            pass
        i = TestItem(id=self.test_id, text=self.test_text)
        t = i.process(self.ended)
        self.assertEqual(t.tags['checklist'], self.test_id)
        self.assertEqual(t.task, self.test_text)
        self.assertEqual(t.create, date.today())

        class TestItem(PastDuePasses, ScheduleFails, ChecklistItem):
            pass
        i = TestItem(id=self.test_id, text=self.test_text)
        t = i.process(self.ended)
        self.assertEqual(t,None)

    def test_finish_in_process(self):
        """Base: test that process ends things appropriately"""
        class TestItem(PastDuePasses, SchedulePasses, ChecklistItem):
            pass
        i = TestItem(id=self.test_id, text=self.test_text)
        t = i.process(self.half_ended)
        # assume task_ended works for now... it is tested other places...
        self.assertTrue(i.task_ended(self.half_ended))
        id, status = self.half_ended.tags["checklist"].partition("_")[::2]
        self.assertEquals(status, "complete")
        t = i.process(self.active)
        self.assertTrue(i.task_ended(self.active))
        id, status = self.active.tags["checklist"].partition("_")[::2]
        self.assertEquals(status, "incomplete")
        t = i.process(self.half_ended_insane)
        self.assertTrue(i.task_ended(self.half_ended_insane))
        id, status = self.half_ended_insane.tags["checklist"].partition("_")[::2]
        self.assertEquals(status, "incomplete")


class TestDaily(TestCase):
    def setUp(self):
        self.test_id = "testdaily"
        self.test_text = "a daily task"
        self.past_due = Task(task=self.test_text, autodate=False)
        self.past_due.create = date.today() - timedelta(days=1)
        self.current = Task(task=self.test_text, autodate = True)

    def test_pastDue_simple(self):
        """Daily past due  and current"""
        d = Daily(id=self.test_id, text=self.test_text)
        self.assertTrue(d.past_due(self.past_due))
        self.assertFalse(d.past_due(self.current))

    # NOTE - for daily this is just the same as past due
    def test_scheduleNext(self):
        """Daily schedule next"""
        d = Daily(id=self.test_id, text=self.test_text)
        self.assertTrue(d.past_due(self.past_due))
        self.assertFalse(d.past_due(self.current))

class TestWeekly(TestCase):
    def setUp(self):
        #monkey patch get_today in checklists
        self.old_get_today = checklists.get_today
        checklists.get_today = lambda: date(2013,12,21) # a saturday
        self.test_id = "testweekly"
        self.test_text = "a weekly task"
        self.past_due = Task(task=self.test_text, autodate=False)
        self.current = Task(task=self.test_text, autodate=False)

    def tearDown(self):
        # remove monkeypatch
        checklists.get_today = self.old_get_today

    def test_pastDue_simple(self):
        """Weekly past due without complete time"""
        w = Weekly(id=self.test_id, text=self.test_text, day=4) #make on fridays
        self.past_due.create = date(2013,12,20) #the previous friday
        self.assertTrue(w.past_due(self.past_due))

    def test_pastDue_simple(self):
        """Weekly current without complete time"""
        w = Weekly(id=self.test_id, text=self.test_text, day=5) #make on sat
        self.current.create = date(2013,12,21) # made today
        self.assertFalse(w.past_due(self.current))

    def test_pastDue_with_ct(self):
        """Weekly past due with complete time"""
        w = Weekly(id=self.test_id, text=self.test_text,
                day=3, complete_time = 2) # thursday
        self.past_due.create = date(2013,12,19) # the preivous thurs
        # today is a saturday, so it past_due should have been done Friday
        self.assertTrue(w.past_due(self.past_due))

    def test_current_with_ct(self):
        """Weekly current wieth complete time"""
        w = Weekly(id=self.test_id, text=self.test_text,
                day=4, complete_time=2) #friday
        self.current.create = date(2013,12,20) # yesterday
        self.assertFalse(w.past_due(self.current))

    def test_rollover(self):
        """Weekly test with a rollover"""
        w = Weekly(id=self.test_id, text = self.test_text,
                day = 5, complete_time=4) #make sat, due wed
        # monkey patch again!
        checklists.get_today = lambda: date(2013,12,25) # a Wed
        self.past_due.create = date(2013,12,21)
        self.assertTrue(w.past_due(self.past_due))

    def test_schedule_next(self):
        """Weekly Simple schedule next"""
        # simple function means simple test. it either schedules because
        # today is the right day, or not. Remember, the test day is a saturday
        w = Weekly(id=self.test_id, text=self.test_text, day=5)
        self.assertTrue(w.schedule_next(self.current))
        w = Weekly(id=self.test_id, text=self.test_text, day=4)
        self.assertFalse(w.schedule_next(self.current))

class TestMonthly(TestCase):
    def setUp(self):
        #monkey patch get_today in checklists
        self.old_get_today = checklists.get_today
        checklists.get_today = lambda: date(2013,12,21) # a saturday
        self.test_id = "testmonthly"
        self.test_text = "a monthly task"
        self.past_due = Task(task=self.test_text, autodate=False)
        self.current = Task(task=self.test_text, autodate=False)

    def tearDown(self):
        # remove monkeypatch
        checklists.get_today = self.old_get_today

    def test_pastDue_simple(self):
        """Monthly past due without complete time"""
        m = Monthly(id=self.test_id, text=self.test_text, day=21)
        self.past_due.create = date(2013,12,20)
        self.assertTrue(m.past_due(self.past_due))

    def test_pastDue_simple(self):
        """Monthly current without complete time"""
        m = Monthly(id=self.test_id, text=self.test_text, day=21) #make on sat
        self.current.create = date(2013,12,21) # made today
        self.assertFalse(m.past_due(self.current))

    def test_pastDue_with_ct(self):
        """Monthly past due with complete time"""
        m = Monthly(id=self.test_id, text=self.test_text,
                day=19, complete_time = 2)
        self.past_due.create = date(2013,12,19)
        # today is a 21st, so it past_due should have been done 20th
        self.assertTrue(m.past_due(self.past_due))

    def test_current_with_ct(self):
        """Monthly current wieth complete time"""
        m = Monthly(id=self.test_id, text=self.test_text,
                day=20, complete_time=2)
        self.current.create = date(2013,12,20) # yesterday
        self.assertFalse(m.past_due(self.current))

    def test_rollover_due(self):
        """Monthly test with a rollover on due"""
        m = Monthly(id=self.test_id, text = self.test_text,
                day = 28, complete_time=2) #make feb 28 due feb 30!
        # monkey patch again!
        checklists.get_today = lambda: date(2013,3,2)
        self.past_due.create = date(2013,2,28)
        self.assertTrue(m.past_due(self.past_due))

        m = Monthly(id=self.test_id, text = self.test_text,
                day = 28, complete_time=3) #make feb 28 due feb 30!
        self.current.create = date(2013,2,28)
        self.assertFalse(m.past_due(self.current))

    def test_rollover_due_hard(self):
        """Monthly test with create day nonexistent in month"""
        # make jan 31. have it 30 days later (feb 30th)
        m = Monthly(id=self.test_id, text = self.test_text,
                day = 31, complete_time=30)
        # monkey patch again!
        checklists.get_today = lambda: date(2013,3,1)
        self.past_due.create = date(2013,1,31)
        self.assertTrue(m.past_due(self.past_due))
        # but it should be current on  the 28th of feb...
        checklists.get_today = lambda: date(2013,2,28)
        self.assertFalse(m.past_due(self.past_due))


    def test_schedule_next(self):
        """Monthly Simple schedule next"""
        # simple function means simple test. it either schedules because
        # today is the right day, or not. Remember, the test day is a saturday
        m = Monthly(id=self.test_id, text=self.test_text, day=21)
        self.assertTrue(m.schedule_next(self.current))
        m = Monthly(id=self.test_id, text=self.test_text, day=15)
        self.assertFalse(m.schedule_next(self.current))
        m = Monthly(id=self.test_id, text=self.test_text, day=30)
        self.assertFalse(m.schedule_next(self.current))

    def test_rollover_sched(self):
        """Monthly test with a rollover on scheduling"""
        m = Monthly(id=self.test_id, text = self.test_text,
                day = 30, complete_time=4) #make on the 30th (or last day)
        # monkey patch again!
        checklists.get_today = lambda: date(2013,2,28) # last day!
        self.assertTrue(m.schedule_next(self.past_due))

class TestFloating(TestCase):
    def setUp(self):
        #monkey patch get_today in checklists
        self.old_get_today = checklists.get_today
        checklists.get_today = lambda: date(2013,12,21) # a saturday
        self.test_id = "testfloating"
        self.test_text = "a floating task"
        self.past_due = Task(task=self.test_text, autodate=False)
        self.current = Task(task=self.test_text, autodate=False)

    def tearDown(self):
        # remove monkeypatch
        checklists.get_today = self.old_get_today

    def test_pastdue_no_ct(self):
        """Floating test past due without CT"""
        f = Floating(id=self.test_id, task=self.test_text)
        self.past_due.create = date(2013,12,20)
        self.current.create = date(2013,12,21)
        self.assertTrue(f.past_due(self.past_due))
        self.assertFalse(f.past_due(self.current))

    def test_pastdue_with_ct(self):
        """Floating test past due with CT"""
        f = Floating(id=self.test_id, task=self.test_text,
                complete_time=3)
        self.past_due.create = date(2013,12,18)
        self.current.create = date(2013,12,20)
        self.assertTrue(f.past_due(self.past_due))
        self.assertFalse(f.past_due(self.current))


    def test_schedule_next_simple(self):
        """Floating test schedule_next immediate schedule"""
        f = Floating(id=self.test_id, task=self.test_text)
        self.past_due.finish = date(2013,12,20)
        self.current.finish = date(2013,12,21)
        self.assertTrue(f.schedule_next(self.past_due))
        self.assertTrue(f.schedule_next(self.current))

    def test_schedule_next_hard(self):
        """Floating test schedule_next wait time"""
        f = Floating(id=self.test_id, task=self.test_text, wait=2)
        self.past_due.finish = date(2013, 12, 18)
        self.current.finish = date(2013, 12,20)
        self.assertTrue(f.schedule_next(self.past_due))
        self.assertFalse(f.schedule_next(self.current))

fake_todo_file = """
2013-12-21 do something +foo +bar @home
x 2013-12-21 2013-12-20 do something +foo @out checklist:exercise
2013-12-20 do time sheet +project @work checklist:reports
2013-12-15 pay bills +finances @home checklist:bills
x 2013-12-18 do something +foo @home
"""

fake_tasks = """
[
  {"type":"daily",
   "id": "exercise",
   "text": "do something +foo @out"
  },
  {"type":"daily",
   "id":"reports",
   "text": "do time sheet +project @work"
  },
  {"type":"monthly",
   "id": "bills",
   "text":"pay bills +finances @home",
   "day":"15",
   "complete_time":3
  }
]
"""
class TestHelpers(TestCase):
    def setUp(self):
        #monkey patch get_today in checklists
        self.old_get_today = checklists.get_today
        checklists.get_today = lambda: date(2013,12,21) # a saturday

    def tearDown(self):
        # remove monkeypatch
        checklists.get_today = self.old_get_today

    def test_load_and_serialize(self):
        """JSON loads correctly, items serialize correctly"""
        json_input = """[
        {"type":"daily",
         "id": "testdaily",
         "text": "a daily task"
        },
        {"type":"weekly",
         "id": "testweekly",
         "text":"a weekly task",
         "day": "mon",
         "complete_time":3
         },
         {"type":"monthly",
          "id": "testmonthly",
          "text":"a monthly task",
          "day": 22,
          "complete_time":4
          },
          {"type":"floating",
           "id":"testfloating",
           "text":"a floating test",
           "wait": 4,
           "complete_time": 2
           }
           ]"""

        items = parse_cl_items(json_input)
        self.assertTrue(isinstance(items[0], Daily))
        self.assertTrue(isinstance(items[1], Weekly))
        self.assertTrue(isinstance(items[2], Monthly))
        self.assertTrue(isinstance(items[3], Floating))
        output_json = serialize_cl_items(items)
        baseval = json.loads(json_input)
        baseval.sort()
        testval = json.loads(output_json)
        testval.sort()

        self.assertEqual(baseval, testval)

    def test_big_process(self):
        """Can actually process todos"""
        try:
            os.makedirs("/tmp/todo_test/")
        except Exception, e:
            print "didn't make dir:", e
            pass
        self.fname = "/tmp/todo_test/todo.txt"
        with open(self.fname, 'w') as fd:
           fd.write(fake_todo_file)
        tf = TodoFile(self.fname)
        tf.open()
        items = parse_cl_items(fake_tasks)
        newlist = process_todos(tf.tasks, items)
        self.assertEqual(len(newlist), 2)
        newids = []
        for t in newlist:
            if not t.tags.has_key("checklist"):
                continue
            cid = t.tags['checklist'].partition('_')[0]
            newids.append(cid)
        self.assertEqual(set(newids), set(['exercise','reports']))
        for t in tf.tasks:
            if not t.tags.has_key("checklist"):
                continue
            cid, status = t.tags['checklist'].partition('_')[::2]
            if cid == 'exercise':
                if t.done and status != 'complete':
                    raise Exception("exercise bad finish!")
            if cid == 'bills':
                if t.done == False or status != "incomplete":
                    raise Exception("bills were complete!")
            if cid == 'reports':
                if t.done == False or status != "incomplete":
                    raise Exception("reports were complete!")

    def test_parse_day(self):
        """does day parsing work?"""
        self.assertEqual(parse_day("Mon"), 0)
        self.assertEqual(parse_day("mon"), 0)
        self.assertEqual(parse_day(0),0)
        self.assertEqual(parse_day("0"), 0)
        self.assertEqual(parse_day('wed'), 2)
