import unittest
from datetime import date

import todo
from todo import Task, TodoFile, get_todo_env

class TestParsing(unittest.TestCase):
    """Parsing tests"""
    def test_empty_line(self):
        x = Task.parse("")
        self.assertEqual(x, None)

    def test_task(self):
        """basic task parsing"""
        todo_line = "foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.priority, "")
        self.assertEqual(task.create, None)
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.task, "foo bar")
        self.assertEqual(set(task.projects), set(["+proj1", "+proj2"]))
        self.assertEqual(set(task.contexts), set(["@context"]))
        self.assertEqual(task.tags, {"tag":"value"})

    def test_dates(self):
        """date handling"""
        todo_line = "2010-2-23 foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.create, date(2010,2,23))
        todo_line = "x 2010-2-23 foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.finish, date(2010,2,23))
        self.assertEqual(task.create, None)
        todo_line = "x 2010-2-23 2010-2-22 foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.finish, date(2010,2,23))
        self.assertEqual(task.create, date(2010,2,22))

    def test_complete(self):
        """completion"""
        todo_line = "x foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.done, True)
        self.assertEqual(task.finish, None)

        todo_line = "x 2013-12-15 foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.done, True)
        self.assertEqual(task.finish, date(2013,12,15))

    def test_leading_space(self):
        """leading spaces"""
        todo_line = " foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.priority, "")
        self.assertEqual(task.create, None)
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.task, " foo bar")
        self.assertEqual(set(task.projects), set(["+proj1", "+proj2"]))
        self.assertEqual(set(task.contexts), set(["@context"]))
        self.assertEqual(task.tags, {"tag":"value"})

        todo_line = " (A) foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.priority, "")
        self.assertEqual(task.create, None)
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.task, " (A) foo bar")
        self.assertEqual(set(task.projects), set(["+proj1", "+proj2"]))
        self.assertEqual(set(task.contexts), set(["@context"]))
        self.assertEqual(task.tags, {"tag":"value"})

        todo_line = " x foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.priority, "")
        self.assertEqual(task.create, None)
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.task, " x foo bar")
        self.assertEqual(set(task.projects), set(["+proj1", "+proj2"]))
        self.assertEqual(set(task.contexts), set(["@context"]))
        self.assertEqual(task.tags, {"tag":"value"})

        todo_line = " 2010-10-2 foo bar +proj1 +proj2 @context tag:value"
        task = Task.parse(todo_line)
        self.assertEqual(task.priority, "")
        self.assertEqual(task.create, date(2010,10,2))
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.task, " foo bar")
        self.assertEqual(set(task.projects), set(["+proj1", "+proj2"]))
        self.assertEqual(set(task.contexts), set(["@context"]))
        self.assertEqual(task.tags, {"tag":"value"})

class TestOutput(unittest.TestCase):
    def test_basic(self):
        """Simple output test"""
        task_str = "foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        self.assertEqual(str(task), task_str)

    def test_simple_done(self):
        """Simple done - no date"""
        task_str = "x foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.done = True
        self.assertEqual(str(task), task_str)

    def test_dated_done(self):
        """Dated done"""
        task_str = "x 2010-10-01 foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.done = True
        task.finish = date(2010,10,1)
        self.assertEqual(str(task), task_str)

    def test_create_finish(self):
        """create and finish dates come out right"""
        task_str = "x 2010-10-01 2010-09-05 foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.done = True
        task.finish = date(2010,10,1)
        task.create = date(2010,9,5)
        self.assertEqual(str(task), task_str)

    def test_priority(self):
        """priority is OK"""
        task_str = "(B) foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.priority = "(B)"
        self.assertEqual(str(task), task_str)

    def test_created(self):
        """creation date works"""
        task_str = "2010-10-01 foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.create = date(2010,10,1)
        self.assertEqual(str(task), task_str)

    def test_created_priority(self):
        """creation date and priority works"""
        task_str = "(A) 2010-10-01 foo bar baz +proj1 +proj2 @context foo:bar"
        task = Task("foo bar baz", projects=['+proj1', '+proj2'],
                     contexts=['@context'], tags={'foo':'bar'})
        task.create = date(2010,10,1)
        task.priority = "(A)"
        self.assertEqual(str(task), task_str)

class TestClass(unittest.TestCase):
    def test_do(self):
        """make sure do function works"""
        task = Task("foo bar")
        task.do()
        self.assertEqual(task.finish, date.today())
        self.assertEqual(task.done, True)

    def test_undo(self):
        """make sure undo works"""
        task = Task("foo bar", autodate=True)
        task.priority = 'a'
        task.do()
        task.do(False)
        self.assertEqual(task.finish, None)
        self.assertEqual(task.done, False)
        self.assertEqual(task.create, date.today())
        self.assertEqual(task.priority, "(A)")

    def test_prioritystuff(self):
        """Priority parsing helpers are good..."""
        t = Task()
        t.priority = "(A)"
        self.assertEqual(t.priority, "(A)")
        t.priority = "A"
        self.assertEqual(t.priority, "(A)")
        t.priority = "a"
        self.assertEqual(t.priority, "(A)")
        t.priority = "(a)"
        self.assertEqual(t.priority, "(A)")
        with self.assertRaises(Exception):
            t.priority = '1'
        with self.assertRaises(Exception):
            t.priority = '(a'
        with self.assertRaises(Exception):
            t.priority = 'foo'
        with self.assertRaises(Exception):
            t.priority = 'qq'
        with self.assertRaises(Exception):
            t.priority = 'ABC'

    def test_autodate(self):
        """make sure we get a good date"""
        t = Task(autodate=True)
        self.assertEqual(t.create, date.today())
        t = Task()
        self.assertEqual(t.create, None)

class TestFile(unittest.TestCase):
    def setUp(self):
        import os
        self.todir = "/tmp/todo_test"
        try:
            os.makedirs(todir)
        except:
            pass
        self.fname = os.path.join(todir,"todo.txt")
        self.file_contents = \
"""(A) 2010-10-01 foo bar baz +proj1
another task +proj1 @with_context
2010-10-02 do a thing +proj2 due:today"""
        # make a clean file
        with open(self.fname, 'w') as fd:
           fd.write(self.file_contents)


    def test_open_parse(self):
        """make sure the file is properly read into the class"""
        f = TodoFile(self.fname)
        f.open()
        task2 = f.tasks[1]
        self.assertEqual(task2.task, "another task")
        self.assertEqual(task2.projects, ['+proj1'])

    def test_stringify(self):
        f = TodoFile(self.fname)
        f.open()
        self.assertEqual(str(f), self.file_contents)

class TestFile(unittest.TestCase):
    def setUp(self):
        import os
        self.todir = "/tmp/todo_test"
        try:
            os.makedirs(todir)
        except:
            pass
        self.cfile = os.path.join(self.todir, ".todo.cfg")
        self.cfile_contents = "TODO_DIR=%s\n" % (self.todir,)
        with open(self.cfile, "w") as fd:
            fd.write(self.cfile_contents)

        self.cffilebackup = todo.CONFIG_FILE
        todo.CONFIG_FILE = self.cfile

    def tearDown(self):
        todo.CONFIG_FILE = self.cffilebackup

    def test_env(self):
        """test that i can get an environment"""

        res = todo.get_todo_env("TODO_DIR")
        self.assertEqual(res, self.todir)


