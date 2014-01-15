todo-scripts
============

Python parser and helper scripts for todo.txt based todo systems.

Todo.txt is a popular textfile based system for handling todos. The scripts in
this project provide some additional funcitonality for todo.txt. The goal is to
be completely optional in use, and not required everywhere todo items are dealt
with. Towards that end there is a Todo class, which can parse todos and save
them completely compliant with the format provided at [todotxt.com].

## Installation

To be documented. But basically just make sure todo.py and checklist.py are in
your python path.

## Todo.py

### Overview

The goal is to provide a nice, pythonic way of working with todos, without
needing a pile of text processing. A todo object seems like a nicer way of
working with todos, and allows for better manipulation, particularly when
things like dates are in native formats. Hopefully this will be the basis of
many todo processing scripts in the future, for creating full featured todo
processing systems without needing to change the format from todotxt.com,
allowing robust usage on "core" devices and servers, while allowing simple
lightweight access on peripheral (etc) devices (like tablets).

### Todo Class
The `Todo` class in `todo.py` represents a single item (meaningful line) from a
`todo.txt` file. It has a static method `parse` which will turn a valid todo
line into the class. It has members for:
* `task` - all the text of the task that isn't metadata
* `priority` - the priority of the item
* `create` - the date an item was created
* `finish` - the date an item was finished
* `done` - a boolean representing the status of the item
* `projects` - a list of `+projectname` tags
* `contexts` - a list of `@contextname` tags
* `tags` - a dict(key=value) of `key:value` tags from the item (for extra info
  helper scripts

it also has a method `do()` which will mark an item as done, and date it with
today.

Finally, converting it to a string (e.g. with `str(item)` will output a valid
line for a todo file.

The constructor takes arguments named after the members listed above. There is
also an optional named attribute: `autodate` which when set to true will give
the item a creation date of today.

### TodoFile class
The class `TodoFile` is for operating on todo.txt formatted files. It is
constructed with a parameter of "filename". It has 2 methods, open and save,
which do the obvious things to the todo file.

It has one member - `tasks` which is a list of tasks from a todo file, in the
ordrer found in the file.

When cast as a string, the TodoFile returns a string, with it's tasks turned
into strings and separated by newlines.

### Other stuff
The `get_todo_env` function will return the requested value from the relevant
todo.cfg. It uses the module level variable `CONFIG_FILE` to determine where
the todo.cfg lives, defaulting to `~/.todo.cfg`.
