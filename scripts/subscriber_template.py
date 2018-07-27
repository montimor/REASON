#!/usr/bin/env python
import rospy

def _rosout_agg_sub():
	rospy.Subscriber('/rosout_agg', Log, callback_rosout_agg_sub)

def callback_rosout_agg_sub(data):
	print(data) #Display the values of the topic, uncomment to show it

if __name__ == '__main__':
	rospy.init_node('Subscriber_node', anonymous=True)
	_rosout_agg_sub()
	rospy.spin()
