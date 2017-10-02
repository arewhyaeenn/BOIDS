from tkinter import *
from time import sleep
from math import sin, cos, atan, pi, fabs
import numpy as np
from collections import deque, Counter


class Environment():
    
    def __init__(self,nfish=0,player='none',
                 width=1535,height=862,
                 fullscreen=True,period=0.01,
                 wallmode='death',pillar_mode='none',
                 pillar_grid_shape=(10,10),pillar_density=.5,
                 food_spawn_period=50,fish_spawn_threshold=10,
                 shark_spawn_threshold=100,shark_max_vitality=2500):
        
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
        
        # walls / terrain / spawn zones
        self.wall = dict()
        self.pillar = dict()
        self.spawn = dict()
        if wallmode == 'death':
            Wall(self,width-9,10,width+1,height-9)
            Wall(self,0,10,10,height-9)
            Wall(self,0,0,width+1,10)
            Wall(self,0,height-9,width+1,height+1)
        elif wallmode == 'wrap':
            WrapBox(self,corners=(0,0,width,height),thickness=20)
        if pillar_mode != 'none':
            self.spawn[0] = ({'x':width-20,'y':(20,height-20),'t':pi})
            self.spawn[1] = ({'x':20,'y':(20,height-20),'t':0})
            self.spawn[2] = ({'x':(20,width-20),'y':20,'t':3*pi/2})
            self.spawn[3] = ({'x':(20,width-20),'y':height-20,'t':pi/2})
            if pillar_mode == 'grid':
                x,y = pillar_grid_shape
                dx = (self.width - 100) / (x+1-pillar_density)
                dy = (self.height - 100) / (y+1-pillar_density)
                w = dx * pillar_density
                sx = dx - w
                l = dy * pillar_density
                sy = dy - l
                xl = 50 + sx
                yt = 50 + sy
                for i in range(x):
                    for j in range(y):
                        self.spawn_pillar(None,(xl,yt,xl+w,yt+l))
                        yt += dy
                    yt = 50 + sy
                    xl += dx

        # fish / occupants
        self.fish = dict()
        self.shark = dict()
        self.shark_vit = shark_max_vitality
        self.food = dict()
        self.food_clock = 0
        self.food_period = food_spawn_period
        self.fish_spawn_threshold = fish_spawn_threshold
        self.shark_spawn_threshold = shark_spawn_threshold
        self.vit = dict()
        
        # neighborhoods
        self.ohood = dict() # neighborhood oval IDs to agents
        self.ihood = dict()
        self.thood = dict()
        
        # expand player controls to all types at some point..
        i = 0
        if player == 'none':
            self.tk.bind('f',self.spawn_fish)
            self.tk.bind('s',self.spawn_shark)
            self.tk.bind('c',self.clear)
            self.tk.bind('p',self.spawn_pillar)
            self.tk.bind('d',self.spawn_food)
            self.tk.bind('b',self.scoreboard)
        elif player == 'fish':
            Fish(self,mode='player',loc='random')
            i += 1
        while i < nfish:
            Fish(self,loc='random')
            i +=1
        
        self.tk.bind('<Return>',self.exit)
        
        # scoreboards
        self.fodeath = Counter()
        self.fdeath = Counter()
        self.sdeath = Counter()
        
        # go time
        self.mainloop()
    
    def mainloop(self):
        
        while self.go:
            self.food_clock += 1
            if self.food_clock == self.food_period:
                self.spawn_food(None)
                self.food_clock = 0
            W = deque(self.wall.values())
            while W:
                wall = W.pop()
                wall.update()
            S = deque(self.shark.values())
            while S:
                shark = S.pop()
                shark.broadcast()
            F = deque(self.fish.values())
            while F:
                fish = F.pop()
                fish.broadcast()
            S = deque(self.shark.values())
            while S:
                shark = S.pop()
                shark.update()
            F = deque(self.fish.values())
            while F:
                fish = F.pop()
                fish.update()
            F = deque(self.food.values())
            while F:
                food = F.pop()
                food.update()
            self.tk.update()
            self.tk.update_idletasks()
            sleep(self.period)
        self.scoreboard(None)
        self.tk.destroy()
    
    def scoreboard(self,event):
        print('Food Eaten :',self.fodeath['eaten'])
        print('Fish Causes of Death:')
        for CoD in self.fdeath:
            print('  ',CoD.ljust(10),':',str(self.fdeath[CoD]).rjust(10))
        print('Shark Causes of Death:')
        for CoD in self.sdeath:
            print('  ',CoD.ljust(10),':',str(self.sdeath[CoD]).rjust(10))
    
    def get_random_spawn_coords(self):
        n = np.random.randint(0,4)
        x = self.spawn[n]['x']
        y = self.spawn[n]['y']
        t = self.spawn[n]['t']
        if type(x) != int:
            x = np.random.randint(*x)
        else:
            y = np.random.randint(*y)
        return((x,y,t))
    
    def spawn_fish(self,event,loc='random'):
        Fish(self,loc=loc,food_to_spawn=self.fish_spawn_threshold)
    
    def spawn_shark(self,event,loc='random'):
        Shark(self,loc=loc,fish_to_spawn=self.shark_spawn_threshold,
              vitality=self.shark_vit)
    
    def spawn_pillar(self,event,coords='random'):
        if coords == 'random':
            radius = np.random.randint(5,int(min(self.width,
                                                 self.height)/20))
            x = np.random.randint(75+radius,self.width-75-radius)
            y = np.random.randint(75+radius,self.height-75-radius)
            coords = (x-radius,y-radius,x+radius,y+radius)
            Wall(self,*coords,mode='pillar')
        else:
            Wall(self,*coords,mode='pillar')
    
    def spawn_food(self,event,coords='random'):
        if coords == 'random':
            x = np.random.randint(10,self.width-10)
            y = np.random.randint(10,self.height-10)
            Fish_Food(self,x,y)
        else:
            Fish_Food(self,*coords)
    
    def exit(self,event):
        self.go = False
    
    def clear(self,event):
        for shark in self.shark.values():
            shark.set_dead('smote')
        for fish in self.fish.values():
            fish.set_dead('smote')
        for pillar in self.pillar.values():
            pillar.set_demo()


class Wall():
    
    def __init__(self,master,x1,y1,x2,y2,mode='wall'):
        self.master = master
        self.can = self.master.can
        self.body = self.can.create_rectangle(x1,y1,x2,y2,fill='red',tags=('wall'))
        self.coords = (x1,y1,x2,y2)
        self.label = 'wall'
        self.mode = mode
        self.set_body_ID(self.body)
        self.alive = True
        
    def set_body_ID(self,ID):
        self.master.label[ID] = 'wall'
        self.master.wall[ID] = self
        if self.mode == 'pillar':
            self.master.pillar[ID] = self
    
    def set_demo(self):
        self.alive = False
    
    # kill fish who crash, tell nearby fish it's here...
    def update(self):
        if self.alive:
            for ID in self.can.find_overlapping(*self.coords):
                label = self.master.label[ID]
                if label in ['thood','ihood']:
                    (x1,y1,x2,y2) = self.coords
                    agent = eval('self.master.'+label+'['+str(ID)+']')
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
                    agent.update_inbox((label[0]+'wall',None,x,y,self.body))
                elif self.master.label[ID] == 'fish':
                    self.master.fish[ID].set_dead('wall')
                elif self.master.label[ID] == 'shark':
                    self.master.shark[ID].set_dead('wall')
        else:
            self.demolish()
                    
    def demolish(self):
        del self.master.label[self.body]
        del self.master.wall[self.body]
        if self.mode == 'pillar':
            del self.master.pillar[self.body]
        self.can.delete(self.body)
        del self


class WrapBox():
    
    def __init__(self,master,corners,thickness):
        
        self.master = master
        self.can = self.master.can
        
        (xl,yt,xr,yb) = corners
        self.top = (xl,yt,xr+1,yt+thickness)
        self.bot = (xl,yb-thickness+1,xr+1,yb+1)
        self.left = (xl,yt+thickness,xl+thickness,yb-thickness)
        self.right = (xr-thickness+1,yt+thickness,xr+1,yb-thickness)
        top = self.can.create_rectangle(*self.top,fill='green')
        bot = self.can.create_rectangle(*self.bot,fill='green')
        left = self.can.create_rectangle(*self.left,fill='green')
        right = self.can.create_rectangle(*self.right,fill='green')
        self.spawn_xl = xl + thickness + 10
        self.spawn_xr = xr - thickness - 11
        self.spawn_yt = yt + thickness + 10
        self.spawn_yb = yb - thickness - 11
        
        self.master.label[top] = 'wrap'
        self.master.label[bot] = 'wrap'
        self.master.label[left] = 'wrap'
        self.master.label[right] = 'wrap'
        
        self.master.wall[top] = self
        self.master.wall[bot] = self
        self.master.wall[left] = self
        self.master.wall[right] = self
        
    def update(self):
        for ID in self.can.find_overlapping(*self.top):
            label = self.master.label[ID]
            if label == 'fish':
                self.master.fish[ID].y = self.spawn_yb
            elif label == 'shark':
                self.master.shark[ID].y = self.spawn_yb
            elif label == 'food':
                self.master.food[ID].y = self.spawn_yb
        for ID in self.can.find_overlapping(*self.bot):
            label = self.master.label[ID]
            if label == 'fish':
                self.master.fish[ID].y = self.spawn_yt
            elif label == 'shark':
                self.master.shark[ID].y = self.spawn_yt
            elif label == 'food':
                self.master.food[ID].y = self.spawn_yt
        for ID in self.can.find_overlapping(*self.left):
            label = self.master.label[ID]
            if label == 'fish':
                self.master.fish[ID].x = self.spawn_xr
            elif label == 'shark':
                self.master.shark[ID].x = self.spawn_xr
            elif label == 'food':
                self.master.food[ID].x = self.spawn_xr
        for ID in self.can.find_overlapping(*self.right):
            label = self.master.label[ID]
            if label == 'fish':
                self.master.fish[ID].x = self.spawn_xl
            elif label == 'shark':
                self.master.shark[ID].x = self.spawn_xl
            elif label == 'food':
                self.master.food[ID].x = self.spawn_xl

class Fish_Food():
    
    def __init__(self,master,x,y):#TODO
        self.master = master
        self.can = master.can
        self.x = x
        self.y = np.random.randint(10,self.master.height-10)
        self.body = self.can.create_rectangle(*self.get_body_coords(),
                                              fill='yellow')
        self.t = pi/30*np.random.randint(0,60)
        self.v = 0.1
        self.alive = True
        self.set_body_ID(self.body)
    
    def set_body_ID(self,ID):
        self.master.label[ID] = 'food'
        self.master.food[ID] = self
    
    def get_body_coords(self):
        return (self.x-2,self.y-2,self.x+2,self.y+2)
    
    def update(self): #TODO
        if self.alive:
            for ID in self.can.find_overlapping(self.x-2,self.y-2,
                                                self.x+2,self.y+2):
                label = self.master.label[ID]
                if label in ['ohood','ihood','thood']:
                    agent = eval('self.master.'+label+'['+str(ID)+']')
                    agent.update_inbox((label[0]+'food',self.t,
                                        self.x,self.y,self.body))
            self.v = 0.01*np.random.randint(20,100)
            self.t = self.t + 0.01*pi*np.random.randint(-10,10)
            self.x += self.v*cos(self.t)
            self.y -= self.v*sin(self.t)
            self.can.coords(self.body,self.get_body_coords())
        else:
            self.die()
    
    def set_dead(self,CoD):
        self.master.fodeath[CoD] += 1
        self.alive = False
    
    def die(self): #TODO
        del self.master.food[self.body]
        del self.master.label[self.body]
        self.can.delete(self.body)
        del self
                

class Fish():
    
    def __init__(self,master,loc='random',mode='auto',velocity=3,agility=pi/10,
                 orad=30,irad=10,trad=5,food_to_spawn=10):
        
        # oop setup
        self.master = master
        self.tk = self.master.tk
        self.can = self.master.can
        self.label = 'fish'
        
        # location / status / movement
        self.alive = True
        self.score = 0
        self.spawn_clock = 0
        self.spawn_threshold = food_to_spawn
        self.v = velocity # velocity (actually speed but who cares)
        self.a = agility # maximum rotation per frame
        if loc == 'random':
            self.x,self.y,self.t = self.master.get_random_spawn_coords()
        else:
            self.x,self.y,self.t = loc
        self.body = self.can.create_polygon(*self.get_body_coord(),
                                            fill='blue')
        # "neighborhoods"
        self.orad = orad
        self.irad = irad
        self.trad = trad
        # outer
        self.ohood = self.can.create_oval(*self.get_ohood_coord(),
                                         width=1.5*self.orad,
                                         outline=self.tk.cget('bg'))
        # inner
        self.ihood = self.can.create_oval(*self.get_ihood_coord(),
                                          width=self.irad,
                                          outline=self.tk.cget('bg'))
        # terrain
        self.thood = self.can.create_oval(*self.get_thood_coord(),
                                          width=self.trad,
                                          outline=self.tk.cget('bg'))
        self.can.lower(self.thood)
        self.can.lower(self.ihood)
        self.can.lower(self.ohood)
        
        # messages / observed info from neighbors
        self.inbox = deque()
        self.weight = {'iwall':5,'twall':20,
                       'ofish':2,'ifish':4,
                       'oshark':10,'ishark':10,
                       'ofood':1,'ifood':3,'tfood':3}
        
        # reference in master
        self.set_body_ID(self.body)
        self.set_ohood_ID(self.ohood)
        self.set_ihood_ID(self.ihood)
        self.set_thood_ID(self.thood)
        
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
    
    def set_thood_ID(self,ID):
        self.master.thood[ID] = self
        self.master.label[ID] = 'thood'
    
    def set_dead(self,CoD):
        self.master.fdeath[CoD] += 1
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
        r = self.orad
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_ihood_coord(self):
        r = self.irad
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_thood_coord(self):
        r = self.trad
        x = self.x + 2*r*cos(self.t)
        y = self.y - 2*r*sin(self.t)
        return(x-r,y-r,x+r,y+r)
        
    def get_loc(self):
        return (self.x, self.y)
    
    def get_overlap_coord(self):
        return (self.x-3,self.y-3,self.x+3,self.y+3)
    
    def update_inbox(self,message):
        self.inbox.append(message)
    
    def broadcast(self):
        for ID in self.can.find_overlapping(*self.get_overlap_coord()):
            label = self.master.label[ID]
            if label[1:] == 'hood':
                agent = eval('self.master.'+label+'['+str(ID)+']')
                if agent != self:
                    agent.update_inbox((label[0]+'fish',self.t,
                                        self.x,self.y,self.body))
            elif label == 'food':
                agent = self.master.food[ID]
                agent.set_dead('eaten')
                self.score += 1
                self.spawn_clock += 1
                if self.spawn_clock == self.spawn_threshold:
                    self.spawn_clock = 0
                    self.master.spawn_fish(None,(self.x,self.y,self.t))
                
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
            wt = {'twall':0,'iwall':0,
                  'ifood':0,'ofood':0,'tfood':0,
                  'ofish':0,'ifish':0,'tfish':0,
                  'oshark':0,'ishark':0}
            stim = {'twall':self.t,'iwall':self.t,
                    'ifood':self.t,'ofood':self.t,'tfood':self.t,
                    'ofish':self.t,'ifish':self.t,'tfish':self.t,
                    'oshark':self.t,'ishark':self.t,}
            while self.inbox:
                label,t,x,y,ID = self.inbox.popleft()
                if label in ['iwall','twall']:
                    wt[label] += 1
                    h = stim[label]
                    dx = self.x - x
                    dy = y - self.y
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
                elif label == 'ofish':
                    wt[label] += 1
                    h = stim[label]
                    while t - h > pi:
                        t -= 2*pi
                    while h - t > pi:
                        t += 2*pi
                    h += (t - h) / wt[label]
                    stim[label] = h
                elif label == 'ifish':
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
                elif label == 'oshark':
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    while dt - t > pi:
                        dt -= 2*pi
                    while t - dt > pi:
                        dt += 2*pi
                    if fabs(dt - t) < pi/2:
                        wt[label] += 1
                        if dt - t > 0:
                            dt = t + pi/2
                        else:
                            dt = t - pi/2
                        while dt - h > pi:
                            dt -= 2*pi
                        while h - dt > pi:
                            dt += 2*pi
                        h += (dt - h) / wt[label]
                    stim[label] = h
                elif label[1:] == 'food':
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
            h = self.t
            net = 1
            for label in wt:
                if wt[label]:
                    w = self.weight[label]
                    net += w
                    dt = stim[label]
                    while h - dt > pi:
                        dt += 2*pi
                    while dt - h > pi:
                        dt -= 2*pi
                    h += w * (dt - h) / (net)
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
            self.can.coords(self.thood,self.get_thood_coord())
        else:
            self.die()
    
    def die(self):
        self.can.delete(self.body)
        self.can.delete(self.ohood)
        self.can.delete(self.ihood)
        self.can.delete(self.thood)
        del self.master.fish[self.body]
        del self.master.ohood[self.ohood]
        del self.master.ihood[self.ihood]
        del self.master.thood[self.thood]
        del self.master.label[self.body]
        del self.master.label[self.ohood]
        del self.master.label[self.ihood]
        del self.master.label[self.thood]
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
    
    def __init__(self,master,loc='random',mode='auto',velocity=3.1,agility=pi/25,
                 orad=100,irad=10,trad=30,fish_to_spawn=25,vitality=2500):
        
        # oop setup
        self.master = master
        self.tk = self.master.tk
        self.can = self.master.can
        self.label = 'shark'
        
        # location / status / movement
        self.alive = True
        self.spawn_clock = 0
        self.spawn_threshold = fish_to_spawn
        self.vitality = vitality
        self.max_vitality = vitality
        self.v = velocity
        self.a = agility
        self.children = 0
        if loc == 'random':
            self.x,self.y,self.t = self.master.get_random_spawn_coords()
        else:
            self.x,self.y,self.t = loc
        self.body = self.can.create_polygon(*self.get_body_coord(),
                                            fill='red')
        self.vitbar = self.can.create_rectangle(*self.get_vitbar_coord(),
                                                fill='green')
        
        # "neighborhoods", outer and inner (inner repels...)
        self.orad = orad
        self.irad = irad
        self.trad = trad
        self.ohood = self.can.create_oval(*self.get_ohood_coord(),
                                         width=1.5*self.orad,
                                         outline=self.tk.cget('bg'))
        self.ihood = self.can.create_oval(*self.get_ihood_coord(),
                                          width=self.irad,
                                          outline=self.tk.cget('bg'))
        self.thood = self.can.create_oval(*self.get_thood_coord(),
                                          width=self.trad,
                                          outline=self.tk.cget('bg'))
        self.can.lower(self.ihood)
        self.can.lower(self.thood)
        self.can.lower(self.ohood)
        
        # messages / observed info from neighbors
        self.inbox = deque()
        self.weight = {'twall':20,
                       'ofish':3,'tfish':4,
                       'oshark':1,'ishark':10}
        
        # reference in master
        self.set_body_ID(self.body)
        self.set_ohood_ID(self.ohood)
        self.set_ihood_ID(self.ihood)
        self.set_thood_ID(self.thood)
        self.set_vitbar_ID(self.vitbar)
        
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
    
    def set_thood_ID(self,ID):
        self.master.thood[ID] = self
        self.master.label[ID] = 'thood'
        
    def set_vitbar_ID(self,ID):
        self.master.vit[ID] = self
        self.master.label[ID] = 'vit'
    
    def get_body_coord(self):
        xf = self.x + 12*cos(self.t)
        yf = self.y - 12*sin(self.t)
        xl = self.x + 6*cos(self.t+(2*pi/3))
        yl = self.y - 6*sin(self.t+(2*pi/3))
        xr = self.x + 6*cos(self.t-(2*pi/3))
        yr = self.y - 6*sin(self.t-(2*pi/3))
        return (xf,yf,xl,yl,xr,yr)
    
    def get_ohood_coord(self):
        r = self.orad
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_ihood_coord(self):
        r = self.irad
        x1 = self.x - r
        y1 = self.y - r
        x2 = self.x + r
        y2 = self.y + r
        return (x1,y1,x2,y2)
    
    def get_thood_coord(self):
        r = self.trad/2
        x = self.x + r*cos(self.t)
        y = self.y - r*sin(self.t)
        return(x-r,y-r,x+r,y+r)
    
    def get_vitbar_coord(self):
        return((self.x-10,self.y+10,
                self.x-10+(20*self.vitality/self.max_vitality),self.y+13))
    
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
        self.vitality -= 1
        if self.vitality == 0:
            self.set_dead('starvation')
        if self.alive:
            wt = {'twall':0,
                  'ofish':0,'ifish':0,'tfish':0,
                  'oshark':0,'ishark':0}
            stim = {'twall':self.t,
                    'ofish':self.t,'ifish':self.t,'tfish':self.t,
                    'oshark':self.t,'ishark':self.t,}
            while self.inbox:
                label,t,x,y,ID = self.inbox.popleft()
                if label == 'twall':
                    wt[label] += 1
                    h = stim[label]
                    dx = self.x - x # target direction x vector
                    dy = y - self.y                
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
                            dt = h
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
                elif label in ['ofish','tfish']:
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
                elif label == 'ifish':
                    self.spawn_clock += 1
                    if self.spawn_clock == self.spawn_threshold:
                        self.master.spawn_shark(None,(self.x,self.y,self.t))
                        self.spawn_clock = 0
                        self.children += 1
                    self.master.fish[ID].set_dead('eaten')
                    self.vitality = min(self.vitality+100,self.max_vitality)
                elif label == 'ishark':
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
                elif label == 'oshark':
                    wt[label] += 1
                    h = stim[label]
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
                    while dt - h > pi:
                        dt -= 2*pi
                    while h - dt > pi:
                        dt += 2*pi
                    h += (dt - h) / wt[label]
                    stim[label] = h
            h = self.t
            net = 1
            for label in wt:
                w = wt[label]
                if w:
                    w = self.weight[label]
                    net += w
                    dt = stim[label]
                    while h - dt > pi:
                        dt += 2*pi
                    while dt - h > pi:
                        dt -= 2*pi
                    h += w * (dt - h) / (net)
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
            self.can.coords(self.thood,self.get_thood_coord())
            self.can.coords(self.vitbar,self.get_vitbar_coord())
        else:
            self.die()
    
    def set_dead(self,CoD):
        self.master.sdeath[CoD] += 1
        self.alive = False
    
    def die(self):
        self.can.delete(self.body)
        self.can.delete(self.ohood)
        self.can.delete(self.ihood)
        self.can.delete(self.thood)
        self.can.delete(self.vitbar)
        del self.master.shark[self.body]
        del self.master.ohood[self.ohood]
        del self.master.ihood[self.ihood]
        del self.master.thood[self.thood]
        del self.master.vit[self.vitbar]
        del self.master.label[self.body]
        del self.master.label[self.ohood]
        del self.master.label[self.ihood]
        del self.master.label[self.thood]
        del self.master.label[self.vitbar]
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

env = Environment(width=500,height=700,period=0.01,wallmode='wrap',
                  pillar_mode='grid',pillar_grid_shape=(3,4),
                  pillar_density=.25,food_spawn_period=3,
                  fish_spawn_threshold=10,shark_spawn_threshold=200,
                  shark_max_vitality=2500,
                  fullscreen=False)