import cmd
from deemon.app.db import DB
from deemon import __version__

class DeemonEditSettings(cmd.Cmd):

    intro = "\nTo exit editor mode without saving changes, type \"exit\"\nTo see a " \
            "list of available options type \"help\""
    prompt = "(deemon edit)> "

    def __init__(self):
        super().__init__()
        self.aliases = {'quit': self.do_exit}

    def do_save(self, arg):
        '''Save modified settings and exit editor mode'''
        print("Settings saved")
        return True

    def do_exit(self, arg):
        '''Exit editor mode without saving changes'''
        return True

    def do_help(self, arg):
        '''List available commands.'''
        if arg in self.aliases:
            arg = self.aliases[arg].__name__[3:]
        cmd.Cmd.do_help(self, arg)

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.aliases:
            self.aliases[cmd](arg)
        else:
            print("*** Unknown syntax: %s" % line)

class DeemonSettings(cmd.Cmd):

    intro = "--== deemon Configuration Editor ==--\nVersion " + __version__ + "\n"
    prompt = "(deemon)> "

    def __init__(self):
        super().__init__()
        self.aliases = {'quit': self.do_exit}
        self.db = DB("/home/seggleston/.config/deemon/releases.db")

    def do_show(self, arg):
        '''Shows current settings'''
        current_settings = self.db.query("SELECT property, value FROM settings")
        for setting in current_settings:
            print(setting)

    def do_edit(self, arg):
        '''Enter editor mode to modify settings'''
        edit_settings = DeemonEditSettings().cmdloop()

    def do_exit(self, arg):
        '''Exit the configuration editor'''
        return True

    def do_help(self, arg):
        '''List available commands.'''
        if arg in self.aliases:
            arg = self.aliases[arg].__name__[3:]
        cmd.Cmd.do_help(self, arg)

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.aliases:
            self.aliases[cmd](arg)
        else:
            print("*** Unknown syntax: %s" % line)

DeemonSettings().cmdloop()
