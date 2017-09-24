from tkinter import *
from time import sleep
from math import sin, cos, atan, pi, fabs
import numpy as np
from collections import deque


class Environment():
    
    def __init__(self,nfish=0,player='none',width=1535,height=862,
                 fullscreen=True,period=0.01):
        
        # setup
        self.tk = Tk()
        if fullscreen:
            self.tk.attributes('-fullscreen',True)
        self.tk.focus_force()
        self.can = Canvas(self.tk,width=width,height=height)
        self.frame = Frame(self.tk,width=width,height=height)
        self.can.pack()
        self.width = width
        self.height = height
        self.period = period
        self.go = True # quit trigger
        
        # categorize other objects as 'fish', 'wall', etc
        self.label = dict()
        
        # walls...
        self.wall = dict()
        Wall(self,width-9,10,width+1,height-9)
        Wall(self,0,10,10,height-9)
        Wall(self,0,0,width+1,10)
        Wall(self,0,height-9,width+1,height+1)
        
        # fish...
        self.fish = dict()
        self.shark = dict()
        self.ohood = dict() # neighborhood oval IDs to agents
        self.ihood = dict()
        i = 0
        if player == 'none':
            self.tk.bind('f',self.spawn_fish)
            self.tk.bind('s',self.spawn_shark)
        elif player == 'fish':
            Fish(self,mode='player',loc='random')
            i += 1
        while i < nfish:
            Fish(self,loc='random')
            i +=1
        
        self.tk.bind('<Return>',self.exit)
        
        # go time
        self.mainloop()
    
    def mainloop(self):
        
        while self.go:
            for wall in self.wall.values():
                wall.update()
            for shark in self.shark.values():
                shark.broadcast()
            for fish in self.fish.values():
                fish.broadcast()
            S = deque(self.shark.values())
            while S:
                shark = S.pop()
                shark.update()
            F = deque(self.fish.values())
            while F:
                fish = F.pop()
                fish.update()
            self.tk.update()
            self.tk.update_idletasks()
            sleep(self.period)
        self.tk.destroy()
    
    def spawn_fish(self,event):
        Fish(self)
    
    def spawn_shark(self,event):
        Shark(self)
    
    def exit(self,event):
        self.go = False


class Wall():
    
    def __init__(self,master,x1,y1,x2,y2):
        self.master = master
        self.can = self.master.can
        self.body = self.can.create_rectangle(x1,y1,x2,y2,fill='red',tags=('wall'))
        self.set_body_ID(self.body)
        self.coords = (x1,y1,x2,y2)
        self.label = 'wall'
        
    def set_body_ID(self,ID):
        self.master.wall[ID] = self
        self.master.label[ID] = 'wall'
    
    # kill fish who crash, tell nearby fish it's here...
    def update(self):
        for ID in self.can.find_overlapping(*self.coords):
            label = self.master.label[ID]
            if label == 'ohood':
                (x1,y1,x2,y2) = self.coords
                agent = self.master.ohood[ID]
                (X,Y) = agent.get_loc()
                if X < x1:
                    x = x1
                elif X > x2:
                    x = x2
                else:
                    x = X
                if Y < y1:
                    y = y1
                elif Y > y2:
                    y = y2
                else:
                    y = Y
                agent.update_inbox(('wall',None,x,y,self.body))
            elif self.master.label[ID] == 'fish':
                self.master.fish[ID].set_dead()
            elif self.master.label[ID] == 'shark':
                self.master.shark[ID].set_dead()


class Fish():
    
    def __init__(self,master,loc='random',mode='auto',velocity=2,agility=pi/10,
                 radius=100):
        
        # oop setup
        self.master = master
        self.tk = self.master.tk
        self.can = self.master.can
        self.label = 'fish'
        
        # location / status / movement
        self.alive = True
        self.v = velocity # velocity (actually speed but who cares)
        self.a = agility # maximum rotation per frame
        if loc == 'random':
            self.x = np.random.randint(20,self.master.width-20)
            self.y = np.random.randint(20,self.master.height-20)
            self.t = np.random.randint(0,12)*pi/6
        else:
            self.x,self.y,self.t = loc
        self.body = self.can.create_polygon(*self.get_body_coord(),
                                            fill='blue')
        # "neighborhoods", outer and inner (inner repels...)
        self.radius = radius
        self.ohood = self.can.create_oval(*self.get_ohood_coord(),
                                         width=self.radius/2,
                                         outline=self.tk.cget('bg'))
        self.ihood = self.can.create_oval(*self.get_ihood_coord(),
                                          width=self.radius/8,
                                          outline=self.tk.cget('bg'))
        self.can.lower(self.ihood)
        self.can.lower(self.ohood)
        
        # messages / observed info from neighbors
        self.inbox = deque()
        self.weight = {'wall':5,'ofish':0.2,'ifish':2,'ishark':5,'oshark':10}
        
        # reference in master
        self.set_body_ID(self.body)
        self.set_ohood_ID(self.ohood)
        self.set_ihood_ID(self.ihood)
        
        # who's gonna play as a single fish anyway...
        if mode == 'player':
            self.update = self.player_update
            self.tk.bind('<Right>',self.right)
            self.tk.bind('<Left>',self.left)
            self.tk.bind('<Up>',self.up)
            self.tk.bind('<Down>',self.down)
        else:
            self.update = self.auto_update
    
    def set_body_ID(self,ID):
        self.master.fish[ID] = self
        self.master.label[ID] = 'fish'
    
    def set_ohood_ID(self,ID):
        self.master.ohood[ID] = self
        self.master.label[ID] = 'ohood'
    
    def set_ihood_ID(self,ID):
        self.master.ihood[ID] = self
        self.master.label[ID] = 'ihood'
    
    def set_dead(self):
        self.alive = False

    # corners of triangular body
    def get_body_coord(self):
        xf = self.x + 6*cos(self.t)
        yf = self.y - 6*sin(self.t)
        xl = self.x + 3*cos(self.t+(2*pi/3))
        yl = self.y - 3*sin(self.t+(2*pi/3))
        xr = self.x + 3*cos(self.t-(2*pi/3))
        yr = self.y - 3*sin(self.t-(2*pi/3))
        return (xf,yf,xl,yl,xr,yr)
    
    def get_ohood_coord(self):
        r = self.radius/2
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_ihood_coord(self):
        r = self.radius/8
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_loc(self):
        return (self.x, self.y)
    
    def get_overlap_coord(self):
        return (self.x-3,self.y-3,self.x+3,self.y+3)
    
    def update_inbox(self,message):
        self.inbox.append(message)
    
    def broadcast(self):
        for ID in self.can.find_overlapping(*self.get_overlap_coord()):
            label = self.master.label[ID]
            if label == 'ohood':
                agent = self.master.ohood[ID]
                if agent != self:
                    agent.update_inbox(('ofish',self.t,self.x,self.y,self.body))
            elif label == 'ihood':
                agent = self.master.ihood[ID]
                if agent != self:
                    agent.update_inbox(('ifish',self.t,self.x,self.y,self.body))
                
    def player_update(self):
        if self.alive:
            self.x += self.v*cos(self.t)
            self.y -= self.v*sin(self.t)
            self.can.coords(self.body,self.get_body_coord())
            self.can.coords(self.hood,self.get_hood_coord())
        else:
            self.die()
    
    def auto_update(self):
        if self.alive:
            net = 1 # net weight, includes own bearing
            h = self.t
            while self.inbox:
                label,t,x,y,ID = self.inbox.popleft()
                if label == 'wall':
                    dx = self.x - x # target direction x vector
                    dy = y - self.y
                    weight = self.weight['wall'] # /(tx**2+ty**2) # maybe make stronger if closer
                    if dx > 0:
                        dt = atan(dy / dx)
                    elif dx < 0:
                        dt = atan(dy / dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
                elif label == 'ofish':
                    weight = self.weight['ofish']
                    while t - h > pi:
                        t -= 2*pi
                    while h - t > pi:
                        t += 2*pi
                    h += weight*(t - h) / (net + weight)
                    net += weight
                elif label == 'ifish':
                    dx = self.x - x # target direction x vector
                    dy = y - self.y
                    weight = self.weight['ifish'] # /(tx**2+ty**2) # maybe make stronger if closer
                    if dx > 0:
                        dt = atan(dy/dx)
                    elif dx < 0:
                        dt = atan(dy/dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
                elif label == 'oshark':
                    weight = self.weight['oshark']
                    dx = self.x - x
                    dy = y - self.y
                    if dx > 0:
                        dt = atan(dy/dx)
                    elif dx < 0:
                        dt = atan(dy/dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - t > pi:
                        dt -= 2*pi
                    while t - dt > pi:
                        dt += 2*pi
                    if fabs(dt - t) >= pi/2:
                        while dt - h > pi:
                            dt -= 2*pi
                        while h - dt > pi:
                            dt += 2*pi
                    else:
                        if dt - t > 0:
                            dt = t + pi/2
                            while dt - h > pi:
                                dt -= 2*pi
                            while h - dt > pi:
                                dt += 2*pi
                        else:
                            dt = t - pi/2
                            while dt - h > pi:
                                dt -= 2*pi
                            while h - dt > pi:
                                dt += 2*pi
                    h += weight*(dt-h) / (net + weight)                            
            while h - self.t > pi:
                h -= 2*pi
            while self.t - h > pi:
                h += 2*pi
            if fabs(h - self.t) <= self.a:
                self.t = h % (2*pi)
            elif h > self.t:
                self.t = (self.t + self.a)%(2*pi)
            else:
                self.t = (self.t - self.a)%(2*pi)
            self.x += self.v*cos(self.t)
            self.y -= self.v*sin(self.t)
            self.can.coords(self.body,self.get_body_coord())
            self.can.coords(self.ohood,self.get_ohood_coord())
            self.can.coords(self.ihood,self.get_ihood_coord())
        else:
            self.die()
    
    def die(self):
        self.can.delete(self.body)
        self.can.delete(self.ohood)
        self.can.delete(self.ihood)
        del self.master.fish[self.body]
        del self.master.ohood[self.ohood]
        del self.master.ihood[self.ihood]
        del self
    
    def right(self,event):
        self.t = self.t - (pi/60)%(2*pi)
    
    def left(self,event):
        self.t = self.t + (pi/60)%(2*pi)
    
    def up(self,event):
        self.v += .1
        
    def down(self,event):
        if self.v>0:
            self.v -= .1
        else:
            self.v = 0


class Shark():
    
    def __init__(self,master,loc='random',mode='auto',velocity=2.25,agility=pi/30,
                 radius=100):
        
        # oop setup
        self.master = master
        self.tk = self.master.tk
        self.can = self.master.can
        self.label = 'shark'
        
        # location / status / movement
        self.alive = True
        self.v = velocity
        self.a = agility
        self.score = 0 # count fish caught
        if loc == 'random':
            self.x = np.random.randint(40,self.master.width-40)
            self.y = np.random.randint(40,self.master.height-40)
            self.t = np.random.randint(0,12)*pi/6
        else:
            self.x,self.y,self.t = loc
        self.body = self.can.create_polygon(*self.get_body_coord(),
                                            fill='red')
        # "neighborhoods", outer and inner (inner repels...)
        self.radius = radius
        self.ohood = self.can.create_oval(*self.get_ohood_coord(),
                                         width=3*self.radius/2,
                                         outline=self.tk.cget('bg'))
        self.ihood = self.can.create_oval(*self.get_ihood_coord(),
                                          width=self.radius/15,
                                          outline=self.tk.cget('bg'))
        self.can.lower(self.ihood)
        self.can.lower(self.ohood)
        
        # messages / observed info from neighbors
        self.inbox = deque()
        self.weight = {'wall':1,'ofish':5,'ifish':0,'oshark':0.5,'ishark':5}
        
        # reference in master
        self.set_body_ID(self.body)
        self.set_ohood_ID(self.ohood)
        self.set_ihood_ID(self.ihood)
        
        # who's gonna play as a single fish anyway...
        if mode == 'player':
            self.update = self.player_update
            self.tk.bind('<Right>',self.right)
            self.tk.bind('<Left>',self.left)
            self.tk.bind('<Up>',self.up)
            self.tk.bind('<Down>',self.down)
        else:
            self.update = self.auto_update
    
    def set_body_ID(self,ID):
        self.master.shark[ID] = self
        self.master.label[ID] = 'shark'
    
    def set_ohood_ID(self,ID):
        self.master.ohood[ID] = self
        self.master.label[ID] = 'ohood'
    
    def set_ihood_ID(self,ID):
        self.master.ihood[ID] = self
        self.master.label[ID] = 'ihood'
    
    def get_body_coord(self):
        xf = self.x + 12*cos(self.t)
        yf = self.y - 12*sin(self.t)
        xl = self.x + 6*cos(self.t+(2*pi/3))
        yl = self.y - 6*sin(self.t+(2*pi/3))
        xr = self.x + 6*cos(self.t-(2*pi/3))
        yr = self.y - 6*sin(self.t-(2*pi/3))
        return (xf,yf,xl,yl,xr,yr)
    
    def get_ohood_coord(self):
        r = self.radius/2
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_ihood_coord(self):
        r = self.radius/12
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_loc(self):
        return (self.x, self.y)
    
    def get_overlap_coord(self):
        return (self.x-10,self.y-10,self.x+10,self.y+10)
    
    def update_inbox(self,message):
        self.inbox.append(message)
    
    def broadcast(self):
        for ID in self.can.find_overlapping(*self.get_overlap_coord()):
            label = self.master.label[ID]
            if label == 'ohood':
                agent = self.master.ohood[ID]
                if agent != self:
                    agent.update_inbox(('oshark',self.t,self.x,self.y,self.body))
            elif label == 'ihood':
                agent = self.master.ihood[ID]
                if agent != self:
                    agent.update_inbox(('ishark',self.t,self.x,self.y,self.body))
                
    def player_update(self):
        if self.alive:
            self.x += self.v*cos(self.t)
            self.y -= self.v*sin(self.t)
            self.can.coords(self.body,self.get_body_coord())
            self.can.coords(self.ohood,self.get_ohood_coord())
            self.can.coords(self.ihood,self.get_ihood_coord())
        else:
            self.die()
    
    def auto_update(self):
        if self.alive:
            net = 1 # net weight, includes own bearing
            h = self.t
            while self.inbox:
                label,t,x,y,ID = self.inbox.popleft()
                if label == 'wall':
                    dx = self.x - x # target direction x vector
                    dy = y - self.y
                    weight = self.weight['wall'] # /(tx**2+ty**2) # maybe make stronger if closer
                    if dx > 0:
                        dt = atan(dy / dx)
                    elif dx < 0:
                        dt = atan(dy / dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
                elif label == 'ofish':
                    weight = self.weight['ofish']
                    dx = x - self.x
                    dy = self.y - y
                    if dx > 0:
                        dt = atan(dy / dx)
                    elif dx < 0:
                        dt = atan(dy / dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
                elif label == 'ifish':
                    self.score += 1
                    self.master.fish[ID].set_dead()
                elif label == 'ishark':
                    dx = self.x - x
                    dy = y - self.y
                    weight = self.weight['ishark']
                    if dx > 0:
                        dt = atan(dy/dx)
                    elif dx < 0:
                        dt = atan(dy/dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
                elif label == 'oshark':
                    dx = self.x - x
                    dy = y - self.y
                    weight = self.weight['oshark']
                    if dx > 0:
                        dt = atan(dy/dx)
                    elif dx < 0:
                        dt = atan(dy/dx) + pi
                    else:
                        if dy > 0:
                            dt = pi/2
                        elif dy < 0:
                            dt = -pi/2
                        else:
                            dt = self.t
                            weight = 0
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += weight*(dt - h) / (net + weight)
                    net += weight
            while h - self.t > pi:
                h -= 2*pi
            while self.t - h > pi:
                h += 2*pi
            if fabs(h - self.t) <= self.a:
                self.t = h % (2*pi)
            elif h > self.t:
                self.t = (self.t + self.a)%(2*pi)
            else:
                self.t = (self.t - self.a)%(2*pi)
            self.x += self.v*cos(self.t)
            self.y -= self.v*sin(self.t)
            self.can.coords(self.body,self.get_body_coord())
            self.can.coords(self.ohood,self.get_ohood_coord())
            self.can.coords(self.ihood,self.get_ihood_coord())
        else:
            self.die()
    
    def set_dead(self):
        self.alive = False
    
    def die(self):
        self.can.delete(self.body)
        self.can.delete(self.ohood)
        self.can.delete(self.ihood)
        del self.master.shark[self.body]
        del self.master.ohood[self.ohood]
        del self.master.ihood[self.ihood]
        del self
    
    def right(self,event):
        self.t = self.t - (pi/60)%(2*pi)
    
    def left(self,event):
        self.t = self.t + (pi/60)%(2*pi)
    
    def up(self,event):
        self.v += .1
        
    def down(self,event):
        if self.v>0:
            self.v -= .1
        else:
            self.v = 0

env = Environment(width=600,height=600,period=0.01)