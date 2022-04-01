import time

import numpy as np
from numpy import ndarray


class FramesDict:
    """
    Frames dictionary, collect the last debug-frame sent from each MU. Implement all utilities methods to insert and
    retrieve the current frame for each MU
    """
    def __init__(self):
        self.d = {}

    def add_frame(self, host_id, frame):
        """
        Save the last frame sent from `host_id`, coupled with current system timestamp
        :param host_id:
        :param frame:
        :return:
        """
        self.d[host_id] = (time.time(), frame)

    def get_frame(self, host_id):
        """
        :param host_id:
        :return: Last frame sent from MU with `host_id`, if there is. Otherwise: `None`
        """
        f = None
        if host_id in self.d:
            _, f = self.d[host_id]
        return f

    def get_frame_no_duplicate(self, host_id, img: ndarray):
        """
        Return the last frame sent, only if the frame differ from given `img` frame
        :param host_id:
        :param img:
        :return:
        """
        f = None
        if host_id in self.d:
            _, f = self.d[host_id]
            # if img.all(f) == f:
            if (img == f).all(where=True):
                f = None
        else:
            raise Exception(f'No more frames of {host_id}')
        return f

    def last_update(self, host_id):
        """
        :param host_id:
        :return: save-timestamp of current `host_id` frame
        """
        t = 0
        if host_id in self.d:
            t, _ = self.d[host_id]
        return t

    def get_streamers(self):
        """
        :return: list of MUs IDs
        """
        return list(self.d.keys())

    def get_all_frames(self, n_col=2):
        """
        :param n_col:
        :return: return a collage of all MU's frames
        """
        if len(self.d) == 0:
            return None
        row_buf = []
        rows = []
        for host in self.d:
            _, frame = self.d[host]
            row_buf.append(frame)
            if len(row_buf) < n_col:
                continue
            h_stack = np.hstack(row_buf)
            rows.append(h_stack)
            row_buf.clear()
        if len(row_buf) > 0:
            while len(row_buf) < n_col:
                row_buf.append(frame)

            h_stack = np.hstack(row_buf)
            rows.append(h_stack)
            row_buf.clear()
        v_stack = np.vstack(rows)
        return v_stack

    def remove_streamer(self, device_id):
        """
        Simply remove dict entry for `device_id` 's frame
        :param device_id:
        :return:
        """
        # print(f'fd.remove_streamer(self, {device_id})')
        rm_streamer = self.d.pop(device_id)
        assert not (device_id in self.d)
