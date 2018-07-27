#!/usr/bin/env python

import rospy
from std_msgs.msg import String

def callback(data):
    rospy.loginfo(data.data)

def listener():
    rospy.Subscriber('chatter', String, callback)

if __name__ == '__main__':
   	rospy.init_node('listener', anonymous=True)
	listener()
	rospy.spin()

