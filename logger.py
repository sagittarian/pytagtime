class Logger:

    def __init__(self, logf, linelen = 80):
        self.logf = logf
        self.linelen = linelen

    def log(self, s):
        '''append a string to the log file'''
        if s and s[-1] != '\n':
            s = s + '\n'
        with open(self.logf, 'a') as f:
            f.write(s)
    slog = log # original name
