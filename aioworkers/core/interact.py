from threading import Thread


class Shell(Thread):
    def run(self):
        from IPython import embed
        context, = self._args
        embed()


def shell(context):
    thread = Shell(args=(context,))
    thread.start()
    return thread
