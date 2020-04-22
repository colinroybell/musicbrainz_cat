class TrackStats:
    def __init__(self):
        self.tracks = 0
        self.time = 0

    def append(self,time):
        self.tracks += 1
        self.time += int(time) // 1000

    def __str__(self):
        hours = self.time // 3600
        minutes = (self.time // 60) % 60
        seconds = self.time % 60

        if hours > 0:
            time_string = "{}:{:0>2d}:{:0>2d}".format(hours,minutes,seconds)
        else:
            time_string = "{}:{:0>2d}".format(minutes,seconds)

        return time_string + "({})".format(self.tracks)
