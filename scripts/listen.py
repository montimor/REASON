#!/usr/bin/env python
import rospy
from std_msgs.msg import String

def call(data):
    rospy.loginfo(data.data)

def listen():
    rospy.Subscriber('chat', String, call)

if __name__ == '__main__':
   	rospy.init_node('listen', anonymous=True)
	listen()
	rospy.spin()

