#!/usr/bin/env python

import rospy
from std_msgs.msg import String

def talker():
    pub = rospy.Publisher('chatter', String, queue_size=10)
    data = "hello world"
    pub.publish(data)
	
def talk():
    pub = rospy.Publisher('chat', String, queue_size=10)
    data = "HELLO WORD"
    pub.publish(data)

if __name__ == '__main__':
	rospy.init_node('talker', anonymous=True)
	while not rospy.is_shutdown():
		talker()
		talk()
