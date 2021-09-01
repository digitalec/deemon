from cleo import Command, Application


class GreetCommand(Command):
    """
    Greets someone

    greet
        {name? : Who do you want to greet?}
        {--y|yell : If set, the task will yell in uppercase letters}
    """

    def handle(self):
        name = self.argument('name')

        if name:
            text = 'Hello {}'.format(name)
        else:
            text = 'Hello'

        if self.option('yell'):
            text = text.upper()

        self.line(text)

application = Application()
application.add(GreetCommand())

if __name__ == "__main__":
    application.run()