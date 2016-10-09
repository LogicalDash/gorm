cdef class TriqueEntry:
    cdef public TriqueEntry next, prev
    cdef public object value
    cdef public int rev
    
    def __cinit__(self, int rev, object value, TriqueEntry prev=None, TriqueEntry nxt=None):
        self.rev = rev
        self.value = value
        self.next = nxt
        self.prev = prev


cdef class Trique:
    cdef TriqueEntry head, waist, tail
    cdef int length

    @property
    def middle(self):
        if self.waist is None:
            return None
        return self.waist.rev, self.waist.value

    @middle.setter
    def middle(self, tuple rv):
        (rev, v) = rv
        if self.waist is None:
            self.head = self.waist = self.tail = TriqueEntry(rev, v)
            self.length = 1
        else:
            self.waist.rev = rev
            self.waist.value = v

    def __cinit__(self, list data=[]):
        self.length = 0
        self.head = None
        self.waist = None
        self.tail = None
        self.extend(data)

    def __len__(self):
        return self.length

    def __iter__(self):
        cdef TriqueEntry here = self.head
        while here is not None:
            yield here.rev, here.value
            here = here.next

    cdef TriqueEntry seekentry(self, int n=0):
        if n == 0:
            return self.waist
        if self.waist is None:
            if self.head is None:
                raise IndexError("nothing to seek through")
            self.waist = self.head
        while n > 0:
            if self.waist.next is None:
                raise IndexError("seek past end of trique")
            self.waist = self.waist.next
            n -= 1
        while n < 0:
            if self.waist.prev is None:
                raise IndexError("seek past start of trique")
            self.waist = self.waist.prev
            n += 1
        return self.waist

    cpdef tuple seek(self, int n=0):
        cdef TriqueEntry ret = self.seekentry(n)
        return ret.rev, ret.value

    cdef TriqueEntry getentry(self, int i=0):
        if i >= 0:
            self.waist = self.head
        elif i <= -1:
            self.waist = self.tail
            i += 1
        self.seek(i)
        return self.waist

    def __getitem__(self, int i):
        cdef TriqueEntry ret = self.getentry(i)
        return ret.rev, ret.value

    def __setitem__(self, int i, tuple rv):
        if i == self.length:
            self.append(rv)
        elif abs(i) > self.length:
            raise IndexError("Set past start/end of trique")
        elif i == 0:
            if self.length == 0:
                self.append(rv)
            else:
                self.head.rev, self.head.value = rv
        elif i == -1 or i == self.length - 1:
            if self.length == 0:
                self.append(rv)
            else:
                self.tail.rev, self.tail.value = rv
        else:
            if i > 0:
                self.waist = self.head
            else:  # i < 0
                self.waist = self.tail
            self.seek(i)
            self.waist.rev, self.waist.value = rv

    def __delitem__(self, int i):
        if self.length == 0:
            raise IndexError("del from empty trique")
        elif i == 0:
            self.head = self.head.next
            self.head.prev = None
            self.length -= 1
        elif i == -1 or i == self.length - 1:
            self.tail = self.tail.prev
            self.tail.next = None
            self.length -= 1
        elif abs(i) >= self.length:
            raise IndexError("del past start/end of trique")
        else:
            if i > 0:
                self.waist = self.head
            else:  # i < 0
                self.waist = self.tail
                i += 1
            self.seek(i)
            self.waist.prev.next = self.waist.next
            self.waist.next.prev = self.waist.prev
            self.waist = self.waist.prev
            self.length -= 1

    cdef appendentry(self, TriqueEntry entry):
        if self.head is None:
            entry.next = entry.prev = None
            self.head = self.waist = self.tail =entry
            self.length = 1
            return
        entry.prev = self.tail
        entry.next = None
        self.tail.next = entry
        self.tail = entry
        self.length += 1

    cpdef append(self, tuple rv):
        self.appendentry(TriqueEntry(*rv))

    cpdef extend(self, object iterable):
        for rev, v in iterable:
            self.appendentry(TriqueEntry(rev, v))

    cdef appendleftentry(self, TriqueEntry entry):
        if self.head is None:
            self.appendentry(entry)
            return
        entry.next = self.head
        entry.prev = None
        self.head.prev = entry
        self.head = entry
        self.length += 1

    cdef insertmiddleentry(self, TriqueEntry entry):
        cdef TriqueEntry nxt
        if self.length <= 1 or self.waist is self.tail:
            self.appendentry(entry)
            self.waist = entry
            return
        nxt = self.waist.next
        self.waist.next = entry
        nxt.prev = entry
        entry.prev = self.waist
        entry.next = nxt
        self.waist = entry
        self.length += 1

    cpdef insertmiddle(self, tuple rv):
        self.insertmiddleentry(TriqueEntry(*rv))

    cpdef insert(self, int i, tuple rv):
        if i < 0:
            self.waist = self.tail
        else:
            self.waist = self.head
        self.seek(i)
        self.insertmiddle(rv)

    cpdef appendleft(self, tuple rv):
        self.appendleftentry(TriqueEntry(*rv))

    cdef TriqueEntry poprightentry(self):
        cdef TriqueEntry ret
        if self.tail is None:
            raise IndexError("pop from empty trique")
        ret = self.tail
        if self.tail.prev is None:
            self.head = self.tail = None
        else:
            self.tail = self.tail.prev
        if ret is self.waist:
            self.waist = self.waist.prev or self.waist.next
        self.length -= 1
        return ret

    cdef TriqueEntry popleftentry(self):
        cdef TriqueEntry ret
        if self.head is None:
            raise IndexError("pop from empty trique")
        ret = self.head
        if ret.next is None:
            self.head = self.tail = None
        else:
            self.head = ret.next
        if ret is self.waist:
            self.waist = self.waist.next or self.waist.prev
        self.length -= 1
        return ret

    cdef TriqueEntry popentry(self, int i=-1):
        cdef TriqueEntry ret, prev, nxt
        if i == 0:
            return self.popleftentry()
        elif i == -1:
            return self.poprightentry()
        elif self.length == 0:
            raise IndexError("pop from empty trique")
        elif i > 0:
            self.waist = self.head
            self.seek(i)
        else:  # i < 0
            self.waist = self.tail
            self.seek(i+1)
        ret = self.waist
        prev = ret.prev
        nxt = ret.next
        prev.next = nxt
        nxt.prev = prev
        self.waist = prev if i < 0 else nxt
        self.length -= 1
        return ret

    cpdef tuple pop(self, int i=-1):
        cdef TriqueEntry ret = self.popentry(i)
        return ret.rev, ret.value

    cpdef tuple popleft(self):
        cdef TriqueEntry ret = self.popleftentry()
        return ret.rev, ret.value

    cdef TriqueEntry popmiddleentry(self, int n=0):
        cdef TriqueEntry ret, prev, nxt
        if n != 0:
            self.seek(n)
        ret = self.waist
        if ret is None:
            raise IndexError("pop from empty trique")
        prev = self.waist.prev
        nxt = self.waist.next
        prev.next = nxt
        nxt.prev = prev
        self.length -= 1
        return ret

    cpdef tuple popmiddle(self, int n=0):
        cdef TriqueEntry ret = self.popmiddleentry(n)
        return ret.rev, ret.value

    cpdef seekrev(self, int rev):
        while self.waist.rev < rev:
            try:
                self.seek(1)
            except IndexError:
                break
        while self.waist.rev > rev:
            try:
                self.seek(-1)
            except IndexError:
                break
        if self.waist.rev > rev:
            raise ValueError("Couldn't seek to a rev earlier than {}".format(self.waist.rev))
