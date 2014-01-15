import re
import subprocess
from datetime import datetime as DT, date

CONFIG_FILE="~/.todo.cfg"

_tagTest = re.compile(r'.+:.+')
_prioTest = re.compile(r'\([A-Z]\)$')
_validPrio = re.compile(r'[A-Z]')

def _makeDate(word):
    if word is None: return None
    if isinstance(word, date): return word
    return DT.strptime(word, "%Y-%m-%d").date()

def _isDate(word):
    # print "date testing:", word
    try:
        _makeDate(word)
    except Exception, e:
        # print "Failed date parse on: %s" % (word,)
        # print "exeption", e
        return False
    return True

def _isPriority(word):
    return bool(_prioTest.match(word))

def _isProject(word):
    return word.startswith("+")

def _isContext(word):
    return word.startswith("@")

def _isTag(word):
    return bool(_tagTest.search(word))

def get_todo_env(key):
    cmd = ". %s; echo $%s"
    cmd %= (CONFIG_FILE, key)
    var = subprocess.check_output([cmd], shell=True)
    return var.strip()

class Task(object):
    def __init__(self, task="", projects=None, contexts=None, tags=None, autodate=False):
        self.priority = ''
        self._create = None
        self._finish = None
        self.task = task
        self.done = False
        self.projects = projects if projects else list()
        self.contexts = contexts if contexts else list()
        self.tags = tags if tags else dict()

        if autodate:
            self.create = date.today()

    # can "undo" - pass false
    def do(self, value=True):
        if bool(value):
            self.done = True
            self.finish = DT.now().date()
        else:
            self.done = False
            self.finish = None

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, value):
        if not value:
            self._priority = ""
            return

        value = value.upper()
        if _isPriority(value):
            self._priority = value
        elif len(value) == 1 and _validPrio.match(value):
            self._priority = "(%s)" % value
        else:
            raise Exception('Bad prio')

    @property
    def create(self):
        return self._create

    @create.setter
    def create(self, val):
        self._create = _makeDate(val)

    @property
    def finish(self):
        return self._finish

    @finish.setter
    def finish(self, val):
        self._finish = _makeDate(val)

    def __str__(self):
        # Question - strip prio as option?
        tok = []
        finish = str(self.finish) if self.finish else ""
        create = str(self.create) if self.create else ""
        if self.done:
            tok.append("x")
            # strip prio because:
            # tood.sh do [TASK]
            # does it
            tok.extend([finish, create, self.task])
        else:
            tok.extend([self.priority, create, self.task])

        tok.extend(self.projects)
        tok.extend(self.contexts)
        tok.extend("%s:%s" % (k,v) for k,v in self.tags.iteritems())
        return " ".join(v for v in tok if v)

    @staticmethod
    def parse(todoline):
        leading_space=False
        bare_words = []
        task = Task()
        if todoline.strip(' \t\n') == "":
            return None
        if todoline.startswith(' '):
            leading_space = True
        tokens = todoline.split(" ")
        if not leading_space:
            # get rid of internal "" tokens
            tokens = [tok for tok in tokens if tok]
        else:
            # preserve leading ws
            leader = []
            while tokens[0] == '':
                leader.append(tokens.pop(0))
            tokens.insert(0, " ".join(leader))

        # Deal with leading space wierdness
        if not leading_space:
            if tokens[0] == 'x':
                task.done = True
                tokens.pop(0)
                if _isDate(tokens[0]):
                    task.finish = tokens.pop(0)
            if _isPriority(tokens[0]):
                task.priority = tokens.pop(0)
        else:
            bare_words.append(tokens.pop(0))

        # creation date still valid for leading space... TODO: verify
        if _isDate(tokens[0]):
            task.create = tokens.pop(0)

        # Now the meat
        for word in tokens:
            if _isProject(word):
                task.projects.append(word)
            elif _isContext(word):
                task.contexts.append(word)
            elif _isTag(word):
                k, v = word.partition(":")[::2]
                task.tags[k] = v
            else:
                bare_words.append(word)
        task.task = " ".join(bare_words)
        return task


class TodoFile(object):
    def __init__(self, filename=""):
        self.filename = filename

    def __str__(self):
        return "\n".join(str(task) for task in self.tasks)

    def open(self):
        try:
            with open(self.filename, 'r') as fd:
                self.tasks = [Task.parse(x.strip()) for x in fd.readlines()]
            self.tasks = [x for x in self.tasks if x is not None]
        except:
            self.tasks = []

    def save(self):
        with open(self.filename, 'w') as fd:
            fd.write(str(self))
