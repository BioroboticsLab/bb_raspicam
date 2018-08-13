#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  5 13:55:08 2017

@author: dominik
"""
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
import csv
import os
import configparser
import skvideo.io

from pipeline import Pipeline
from pipeline.objects import Image, Positions, Orientations, Saliencies, IDs
from  pipeline.pipeline import get_auto_config
from pipeline.stages import ResultCrownVisualizer

# calculate average distance from 0.5 of the elements of a bee's ID (normalized to a maximum of 1.0)
def average_confidence(ID):
    return (sum([abs(0.5-x) for x in ID])/len(ID))*2

# round detected bee ID with values between 0 and 1 to either 0 or 1
def id_to_binary(ID):
    ID_bin=[]
    for digit in ID:
        ID_bin.append(np.round(digit))
    return ID_bin

# Representation of a single detected Bee
class Event:
    # parameters
    # ------------------
    # ID: Binary code on the bee's tag
    # Position: x,y-Tuple of Pixel Coordinates as returned by the pipeline
    # evt_id:  serial number of the Event
    # time: current utc timestamp
    def __init__(self, ID, Position, 
                 evt_id, time):
        self.id=[id_to_binary(ID)]
        self.pos=Position
        self.age=0
        self.event_id=evt_id
        self.valid=True
        self.detections=1
        self.first_detection = time
        
    # unused
    def equals(self, ID):
        return id_to_binary(ID)==self.id
    
    #update Event with new ID and Position 
    def update(self, ID, Position):
        self.age=0
        self.id.append(id_to_binary(ID))
        self.pos=Position
        self.valid=True
        self.detections+=1
    
    # returns current Pixel coordiinates as x,y-Tuple 
    def get_position(self):
        return (int(self.pos[1]),int(self.pos[0]))
    
    # Set event as invalid if there was no matching detection in the current frame
    def invalidate(self):
        self.valid=False
    
    # TODO: make age limit configurable, possibly do this check in the main code (different age limits for candidates and active events)
    def is_active(self):
        return self.age < 5
    
    # returns serial id for event
    def get_event_id(self):
        return self.event_id
    
    # returns bit-by-bit median of all associated binary ids to ignore false detections
    def get_median_id(self):
        id=[]
        for i in range(len(self.id[0])):
            id.append(np.median([id_candidate[i] for id_candidate in self.id]))
        return id
    
    #returns euclidian distance between the event's Position and the Position given as argument
    def distance(self, position):
        return np.sqrt((self.pos[0]-position[0])**2+(self.pos[1]-position[1])**2)
    
    # save information and image of this event to file
    def save(self,csvwriter,time,feeder_id):
        csvwriter.writerow([self.event_id, feeder_id, self.get_median_id(),self.id, self.first_detection, time, self.detections])
        cv2.imwrite("./images/"+str(self.event_id)+".png", self.image)

    # change the image of this event, will crop an area at the current position from the frame given as argument
    def set_image(self,frame):
        self.image = frame[int(self.pos[0])-50:int(self.pos[0])+50,int(self.pos[1])-50:int(self.pos[1])+50]

class FileLoader:
    # parameters
    # ------------------
    # id: camera id, set in config file
    # address: ip address of raspicam unit, set in config file
    def __init__(self,id,address):
        self.config=configparser.ConfigParser()
        self.config.read('server.cfg')
        self.old_events=[]
        self.old_event_candidates=[]
        self.last_download=None
        self.last_videotime=0
        self.address=address
    # download all files in set video directory
    def getFiles(self):
        filenum=len(os.listdir(self.config['General']['videodir']))
        os.system('sshpass -p \'%s\' scp -r %s@%s:%s %s'%(self.config['Feeders']['password'],self.config['Feeders']['username'],self.address,self.config['Feeders']['remotedir'],"./"))
        files_downloaded=len(os.listdir(self.config['General']['videodir']))-filenum
        if files_downloaded>0:
            self.last_download=time.time()
            for file in os.listdir(config['General']['videodir']):
                os.system('sshpass -p \'%s\' ssh %s@%s %s'%(self.config['Feeders']['password'],self.config['Feeders']['username'],self.address,'rm ' + self.config['Feeders']['remotedir']+"/"+file))
        elif self.last_download==None:
            pass
        # save remaining events if no file was available for download and the last download was too long ago.
        elif time.time()-self.last_download>int(self.config['General']['max_time_between_videos']):
            for event in events:
                event.save(csvwriter,self.last_videotime)
    # store unfinished events from last video for use on a later one
    def storeEvents(self,events,event_candidates,videotime):
        self.old_events=events
        self.old_event_candidates=event_candidates
        self.last_videotime=videotime
    # return previously stored events
    def getEvents(self):
        return (self.old_events,self.old_event_candidates,self.last_videotime)

config=configparser.ConfigParser()
config.read('server.cfg')
feeders={}
ids=config['Feeders']['feeder_ids'].split(',')
addresses=config['Feeders']['feeder_addresses'].split(',')
for i in range(len(ids)):
    feeders[ids[i]]=FileLoader(ids[i],addresses[i])

pipeline = Pipeline([Image], [Positions, Orientations, Saliencies, IDs], **get_auto_config())
print("Pipeline initialized")
framenum=0
vis=ResultCrownVisualizer()

event_num=int(config['General']['last_event_id'])
previous=None
last_time=time.time()
csvfile= open(config['General']['csvfile'], 'a')
csvwriter = csv.writer(csvfile)
running=True
while(running):
    for feeder in feeders.keys():
        print("Downloading videos from feeder with ID: "+feeder)
        feeders[feeder].getFiles()
    for file in os.listdir(config['General']['videodir']):
        fileinfo=file.split('.')[0].split('_')
        feeder_id=fileinfo[0]
        videotime=datetime.strptime(fileinfo[1],"%Y-%m-%d-%H-%M-%S")
        
        # get starting time for new video and restore old events if time difference is short enough, save event data otherwise.
        events,event_candidates,last_videotime=feeders[feeder_id].getEvents()
        if not last_videotime==0 and videotime-last_videotime>timedelta(seconds=int(config['General']['max_time_between_videos'])):
            for event in events:
                event.save(csvwriter,last_videotime)
            events,event_candidates=[],[]
        reader = skvideo.io.FFmpegReader(config['General']['videodir']+"/"+file)
        video=reader.nextFrame()
        
        for frame in video:
            try:
                for i in range(int(config['General']['frameskip'])):
                    frame=next(video)
            
                last_time=time.time()
                framenum+=1
                
                # Video is grayscale, choose arbitrary color channel for grayscale frame
                gray=frame[:,:,0]
                
                #add padding around frame for detection of bees near the border
                small_border=np.zeros((np.shape(gray)[0]+100,np.shape(gray)[1]+100),dtype='uint8')
                cv2.copyMakeBorder(gray,50,50,50,50,cv2.BORDER_CONSTANT,small_border,0)
                
                results=pipeline([small_border])
                
                
                results_filtered={'Positions':[],'Orientations':[],'Saliencies':[],'IDs':[]}
                for i in range(len(results[IDs])):
                    #Only process detections above a set confidence level
                    if average_confidence(results[IDs][i])>float(config['General']['minimum_confidence']):
                        results_filtered['Positions'].append(results[Positions][i])
                        results_filtered['Orientations'].append(results[Orientations][i])
                        results_filtered['Saliencies'].append(results[Saliencies][i])
                        results_filtered['IDs'].append(results[IDs][i])
                        
                        #find closest event to detection and update it if distance is small enough
                        distance=float('inf')
                        match=None
                        for event in events:
                            evt_dist=event.distance(results[Positions][i])
                            if evt_dist<distance:
                                distance=evt_dist
                                match=event
                        print("distance:",distance)
                        if distance <= int(config['General']['max_distance']):
                            match.update(results[IDs][i],results[Positions][i])
                        # if no matching event is found, attempt to match uniniitialized event candidates
                        else:
                            distance_cand=float('inf')
                            match=None
                            for event in event_candidates:
                                evt_dist=event.distance(results[Positions][i])
                                if evt_dist<distance:
                                    distance_cand=evt_dist
                                    match=event
                            if distance_cand<=int(config['General']['max_distance']):
                                match.update(results[IDs][i],results[Positions][i])
                            # if no event or candidate is found, generate new candidate
                            else:
                                event_candidates.append(Event(results[IDs][i],results[Positions][i],-1,videotime))
                                
                # age all events and candidates that have not been matched in the last frame.
                # generate events from candidates that have been detected often enough
                for event in event_candidates:
                    if not event.valid:
                        event.age+=1
                    else:
                        event.invalidate()
                    if event.detections>2:
                        event_num+=1
                        config['General']['last_event_id']=str(event_num)
                        with open('server.cfg', 'w') as configfile:
                            config.write(configfile)
                        event.event_id=event_num
                        event.set_image(small_border)
                        events.append(event)
                for event in events:
                    if not event.valid:
                        event.age+=1
                        if not event.is_active():
                            event.save(csvwriter,videotime,feeder_id)
                            csvfile.flush()
                    else:
                        event.invalidate()
                # remove inactive events
                events=[event for event in events if event.is_active()]
                event_candidates=[event for event in event_candidates if event.is_active() and event.detections<=2]
                            
                # Visualize current detections
                if config['General']['show_visualization']=='1':
                    overlay, = vis(small_border,results[Positions],results[Orientations],results[IDs])
                    overlay_filtered, = vis(small_border,np.asarray(results_filtered['Positions']),np.asarray(results_filtered['Orientations']),np.asarray(results_filtered['IDs']))
                    alpha = overlay[:, :, 3,np.newaxis]
                    alpha_filtered = overlay_filtered[:, :, 3,np.newaxis]
                    image_rgb = cv2.cvtColor(small_border,cv2.COLOR_GRAY2RGB)*(1-alpha)+overlay[:,:,:3]*alpha*255
                    image_rgb_filtered = cv2.cvtColor(small_border,cv2.COLOR_GRAY2RGB)*(1-alpha_filtered)+overlay_filtered[:,:,:3]*alpha_filtered*255
                    
                    for event in events:
                        cv2.putText(image_rgb_filtered,str(event.get_event_id()),event.get_position(),cv2.FONT_HERSHEY_SIMPLEX,1,(244, 185, 107),2)
                    print("average confidence values for detections:")
                    if len(results[IDs]>0):
                        for ID in results[IDs]:
                            print(average_confidence(ID))
                            
                    # Uncomment to show all detections
                    #cv2.imshow('bienen',image_rgb.astype('uint8'))
                    #cv2.waitKey(1)
                    
                    cv2.imshow('bienen_filtered',image_rgb_filtered.astype('uint8'))
                    cv2.waitKey(1)
                videotime+=timedelta(milliseconds=int(config['General']['frameskip'])/int(config['General']['fps'])*1000)
            except:
                pass
        
        #after Video ends, store remaining events and move video to archive
        feeders[feeder_id].storeEvents(events,event_candidates,videotime)
        os.rename(config['General']['videodir']+"/"+file,config['General']['archive_dir']+"/"+file)
        
csvfile.close();
cv2.destroyAllWindows()
