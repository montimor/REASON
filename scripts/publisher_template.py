#!/usr/bin/env python
import rospy

def _rosout_agg_pub():
	pub = rospy.Publisher('/rosout_agg', Log, queue_size=10)
	data = Log() #Initialize the message to publish
	#Insert here the modifications of the message (do it manually or call a function modifying "data")
	
	
	pub.publish(data) #Publish your data

if __name__ == '__main__':
	rospy.init_node('Publisher_node', anonymous=True)
	rate = rospy.Rate(10)
	while not rospy.is_shutdown():
		_rosout_agg_pub()
		rate.sleep()
