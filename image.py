#!/usr/bin/python
#__*__coding:utf-8__*__

import cv2
import numpy as np
import math
from copy import deepcopy
from serial import Serial
import time
import timeit
import logging
from PIL import ImageFont

CIRCLE_DIA = 2.9
OPEN = [0xA0, 0x01, 0x01, 0xA2]
CLOSE = [0xA0, 0x01, 0x00, 0xA1]

servers = '10.16.0.85'
dbname = 'ignitions'
user = 'ignitions'
pwd = 'ignitions'


# create logging
# img_logger = logging.getLogger("mainApp.img")

class Img():
    def __init__(self):
        ##################################################
        # logger
        ###################################################
        # self.logger = logging.getLogger('mainApp.img.Img')
        # self.logger.debug("Creating an logger instance of Img")

        ###################################################
        # img shape and size channel etc
        ###################################################
        #self.img = cv2.imread('a.jpg')
        self.img = np.zeros((600,800),np.uint8)
        self.img_bin = np.zeros((600,800),np.uint8)
        self.roiList = []
        self.scale = 1
        self.rows = 0
        self.cols = 0
        self.pos = [0, 0]
        self.channel = 0
        self.size = 0
        self.dtype = None
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        ###################################################
        # analysis param
        ###################################################
        self.gauss = 5
        self.canny_min = 50
        self.canny_max = 99
        self.bin_threshold = 180
        self.lineThreshold = 300
        self.circleDiaMin = 20
        self.circleDiaMax = 160
        self.circleThreshold = 50
        self.circleVote = 90
        self.circleDist = 30
        self.displayEdage = False
        self.currentBinThreshold = 180
        self.adjustPostive = False
        self.adustNegative = False

        ###################################################
        # result data
        ###################################################
        self.wid_1 = 0
        self.wid_2 = 0
        self.dist_0 = 0
        self.dist_1 = 0
        self.dist_2 = 0
        self.dist_3 = 0
        self.msg = ""
        self.dia = 1
        self.counters = None
        self.lineResult = None
        self.circle_list_0 = []
        self.line_list_0 = []
        self.circle_list_1 = []
        self.line_list_1 = []
        self.circle_list_2 = []
        self.line_list_2 = []
        self.circle_list_3 = []
        self.line_list_3 = []


        self.label_height = 0
        self.label_width = 0

        ###################################################
        # serial port
        ###################################################

        self.COM = 'COM15'
        try:
            self.ser = Serial(self.COM, 9600, timeout=0.5)
            # self.logger.info("Create serial port: %s",self.COM)
        except Exception as e:
            self.ser = None
            # self.logger.info("Failed to create serial port.")



    def setImg(self,img):
        """
        设置图像
        :param img:
        :return:
        """
        self.img = img

    def getImageSize(self):
        """
        get image size and shape
        :return:
        """
        self.rows,self.cols,self.channel = self.img.shape
        self.size,self.dtype = self.img.size,self.img.dtype
        print ('rows/rols',self.rows,self.cols,self.size,self.dtype)
        # self.logger.debug("Image rol=%s,cols=%s", self.rows,self.cols)

    def cutImage(self,top,bottom,left,right):
        """
        剪切图像
        :param top:
        :param bottom:
        :param left:
        :param right:
        :return:
        """
        cut_img = self.img[top:bottom,left:right] # top,bottom,left,right 原始大小：1944，2592
        # self.logger.debug("Cut to row %s to row %s; col %s to col %s",top,bottom,left,right)
        return cut_img

    def resize(self, img, scale):
        """
        按比例缩放图片
        :param img:
        :param scale:
        :return:
        """
        # # 下面的 None 本应该是输出图像的尺寸，但是因为后边我们设置了缩放因子
        # # 因此这里为 None
        # res = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # # OR
        # # 这里呢，我们直接设置输出图像的尺寸，所以不用设置缩放因子
        # height, width = img.shape[:2]
        # res = cv2.resize(img, (2 * width, 2 * height), interpolation=
        cols = int(self.cols * scale)
        rows = int(self.rows * scale)
        return cv2.resize(img, (cols, rows), interpolation=cv2.INTER_CUBIC)

    def scale_cal(self):
        height_scale = round(self.label_height / self.rows, 2)
        print("Lab image height =", self.label_height, "camera image height =", self.rows, "scale =", height_scale)

        width_scale = round(self.label_width / self.cols, 2)
        print("Lab image width =", self.label_width, "camera image width =", self.cols, "scale =", width_scale)
        if height_scale < width_scale:
            self.scale = height_scale
        else:
            self.scale = width_scale
        print("finally scale =", self.scale)



    def gaussianblur(self,img):
        if self.gauss % 2 == 0:
            self.gauss = self.gauss + 1
        else:
            self.gauss = self.gauss
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(img_gray, (self.gauss, self.gauss), 0)  # gauss must be positive and odd
        #kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # 椭圆结构
        #kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))  # 十字结构
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # 矩形结构
        # perform a dilation erosion to close gaps in between object edges
        d = cv2.dilate(blur, kernel, iterations=1)
        # 膨胀 itereation;迭代
        blur = cv2.erode(d, kernel, iterations=1)
        # self.logger.info("Gaussian blur with %s",self.gauss)
        # cv2.imshow('Blur',blur)
        # cv2.waitKey(0)
        return blur

    def threshold(self,blur_img,threshold, method = cv2.THRESH_BINARY_INV):
        """
        :param method: cv2.THRESH_BINARY, CV2.THRESH_BINARY_INV,cv2.THRESH_TRUNC,cv2.THRESH_TOZERO,cv2.THRESH_TOZERO_INV
        :return:
        """

        # ret, thresh1 = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        # ret, thresh2 = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        # ret, thresh3 = cv2.threshold(img, 127, 255, cv2.THRESH_TRUNC)
        # ret, thresh4 = cv2.threshold(img, 127, 255, cv2.THRESH_TOZERO)
        # ret, thresh5 = cv2.threshold(img, 127, 255, cv2.THRESH_TOZERO_INV)
        # self.img = cv2.adaptiveThreshold(self.img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, \
        #                             cv2.THRESH_BINARY, 11, 2)

        ret, img_bin = cv2.threshold(blur_img, threshold, 255, method)
        return ret,img_bin

    def findFrame(self,img, img_bin):
        circle_list = []
        line_list = []
        try:
            # cv2.imshow("img_bin:", img_bin)
            # cv2.waitKey(0)
            #image, contours, hierarchy = cv2.findContours(self.img_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
            contours,hierarchy = cv2.findContours(img_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            #self.img = cv2.drawContours(self.img, contours, -1, (255, 0, 0), 10)
            for c in contours:
                if cv2.contourArea(c) < 300:
                    continue

                # cnt = c
                # #画最小矩形
                # rect = cv2.minAreaRect(cnt)
                # box = cv2.boxPoints(rect)
                # box = np.int0(box)
                # print('box=', [box])
                # self.img = cv2.drawContours(self.img, [box], 0, (255, 0, 0), 2)

                # epsilon = 0.1 * cv2.arcLength(cnt, True)
                # approx = cv2.approxPolyDP(cnt, epsilon, True)
                #cv2.polylines(self.img, [approx], True, (0, 255, 0), 3)
                x, y, w, h = cv2.boundingRect(c)
                print("x,y,x+w,y+h======", x, y, x+w, y+h)
                if 300 <= cv2.contourArea(c) < 12000:
                    circle_list.append([x, y, w, h])
                elif 12000 <= cv2.contourArea(c):
                    line_list.append([x, y, w, h])
                # cv2.imshow("before:",img)
                # cv2.waitKey(0)
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 4)

                # cv2.imshow("after:", img)
                # cv2.waitKey(0)
            print("circle_list", circle_list)
            return circle_list, line_list
        except Exception as e:
            print("Find counter exception:", e)
            # self.logger.info("Did not find any frame!")

    def puzzle(self, img, top, bottom, left, right):
        self.img[top:bottom, left:right] = img

    def edageDetect(self):
        # cv2.imshow('bin',self.resize(self.img_bin))
        # cv2.waitKey(0)
        self.edges = cv2.Canny(self.img_bin, self.canny_min, self.canny_max)
        # self.logger.info("Edage detect with Canny_min = %s, Canny_max = %s",self.canny_min,self.canny_max)

    def displayChoice(self):
        if self.displayEdage:
            self.displayImg = self.img_bin
            print ('Display original image')
            # self.logger.info("Display original image...")
        else:
            self.displayImg = self.img
            print ('Display edage')
            # self.logger.info("Display edage...")

    def findLines(self,img):
        #self.lines = cv2.HoughLines(self.edges, 1, np.pi /360, self.lineThreshold)
        self.lines = cv2.HoughLinesP(img, 1, np.pi / 360, self.lineThreshold,0,10,10) #100 指线段最短长度，#10指线段之间的间隔
        if self.lines!=None:
            print('Find %s hough lines with threshold = %s'% (len(self.lines),self.lineThreshold))
            # self.logger.info("Find %s hough lines with threshold= %s",len(self.lines),self.lineThreshold)
            return True
        else:
            print ('Did not find any lines')
            # self.logger.info("Didn't find any lines with threshold = %s", self.lineThreshold)
            return False

    def cleanLine(self,lines,img,leftSide):
        """

        :param lines:
        :param img:
        :param leftSide: leftSide = True, keep left side, otherwise keep right side
        :return:
        """
        self.slope = []
        self.slopedegree = []
        self.slopeline = []
        lineResult =[]
        print('line=', type(lines), lines)
        try:
            lineList = lines.tolist()
        except Exception as e:
            lineList = []
            print("line to list failed", e)
        print('Totally', len(lineList), ' lines before clean', lines)
        i = 0
        j = 0
        lineResult = deepcopy(lineList)
        for line in lineList:
            print('index =', lineList.index(line))
            print(line)
            for x1, y1, x2, y2 in line:
                if np.abs(x1 - x2) > 5:
                    lineResult.remove(line)
                    # cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    print(line, 'removed0')
                    continue
                else:
                    pass
                if leftSide: # keep left, remove right
                    if x1 > (img.shape[1] / 2) or x2 > (img.shape[1] / 2):
                        lineResult.remove(line)
                        # cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        print(line, 'removed1')
                    else:
                        cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 4)
                else:  # keep right, remove left
                    if x1 < (img.shape[1] / 2) or x2 < (img.shape[1] / 2):
                        lineResult.remove(line)
                        #cv2.line(img, (x1, y1), (x2, y2), (255, 255, 0), 9)
                        # cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        print(line, 'removed2', "x1=",x1,"img.shape[1]/2= ",img.shape,img.shape[1]/2)
                    else:
                        cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 4)
        # cv2.imshow("line =",img)
        # cv2.waitKey(0)
                    # self.logger.info('Find %s slope line, line = %s, slope degree =%s',j, line, self.slopedegree)



        return lineResult
                # slope=[(y2-y1)/(x2-x1) for line in lines for x1,y1,x2,y2 in line]
        # img = self.resize(img,1/5)
        # cv2.imshow("imgg",img)
        # cv2.waitKey(0)

    def rotate(self):
        if self.lineResult==None:
            print ('Did not rotate, because did not find any lines')
            # self.logger.info("Did not rotate, because did not find any lines")
        elif self.slope==None:
            print ('Did not rotate, because did not find any slope lines')
            # self.logger.info ('Did not rotate, because did not find any slope lines')
        else:
            rotateDegree = 90 - math.degrees(np.arctan(np.mean(self.slope)))
            if len(self.slope) > int(len(self.lineResult) *6/10) and rotateDegree < 5:
                M = cv2.getRotationMatrix2D((self.cols / 2, self.rows / 2),
                                            -rotateDegree, 1)
                self.edges = cv2.warpAffine(self.edges, M, (self.cols, self.rows))
                self.img = cv2.warpAffine(self.img, M, (self.cols, self.rows))
                self.displayChoice()
                #cv2.imwrite('rotated.png', self.img)
                # self.blur = self.gaussianblur()
                # self.edges = self.edageDetect()
                self.findLines()
                self.cleanLine()
                print('>>>>>>>>>>>>ratated', math.degrees(np.arctan(np.mean(self.slope))),
                      90 - math.degrees(np.arctan(np.mean(self.slope))))
                print ('Rotated %d degrees'% rotateDegree)
                # self.logger.info("Rotated %s degree.",rotateDegree)
            else:
                print ('Do not need to rotate, because slope lines are less than 60%')

    def findCircles(self):
        # cv2.HoughCircles(image, method, dp, minDist[, circles[, param1, param2[, minRadius[, maxRadius]]]]])
        # image
        # 不用多说，输入矩阵
        # method
        # cv2.HOUGH_GRADIENT
        # 也就是霍夫圆检测，梯度法
        # dp
        # 计数器的分辨率图像像素分辨率与参数空间分辨率的比值
        # （官方文档上写的是图像分辨率与累加器分辨率的比值，它把参数空间认为是一个累加器，毕竟里面存储的都是经过的像素点的数量），
        # dp = 1，则参数空间与图像像素空间（分辨率）一样大，dp = 2，参数空间的分辨率只有像素空间的一半大
        # minDist
        # 圆心之间最小距离，如果距离太小，会产生很多相交的圆，如果距离太大，则会漏掉正确的圆
        # param1
        # canny检测的双阈值中的高阈值，低阈值是它的一半
        # param2
        # 最小投票数（基于圆心的投票数）
        # minRadius
        # 需要检测圆的最小半径
        # maxRadius
        # 需要检测圆的最大半径
        print ("Find circle canlled")
        self.circles = cv2.HoughCircles(self.edges, cv2.HOUGH_GRADIENT, 2, self.circleDist, param1=self.circleThreshold,
                                   param2=self.circleVote,
                                   minRadius=self.circleDiaMin, maxRadius=self.circleDiaMax)
        if self.circles!=None:
            print ('Find',len(self.circles) ,'circles' )
            # self.logger.info("Find %s circles.",len(self.circles))
            # self.logger.debug("Find %s circles, with circledist=%s, circleThreshold=%s,circleVote=%s,circleDiamin=%s,circleDiaMax=%s",
                              # len(self.circles),self.circleDist,self.circleThreshold,self.circelVote,self.circleDiaMin,self.circleDiaMax)
            return True
        else:
            print ('Did not find any circles')
            # self.logger.info("Did not find any circles.")
            return False

    def printCircles(self):
        DiaSum = 0
        circle_center_x = []  # 圆心横座标
        circle_center_y = []  # 圆心纵座标
        self.l_circle_center_x = []  # 图像左半边圆的圆心横坐标
        self.r_circle_center_x = []  # 图像右半边圆的圆心横坐标
        for i in self.circles[0, :]:
            if 1042 < i[0] < int(self.cols / 2):
                self.l_circle_center_x.append(i[0])
                circle_center_x.append(i[0])
                circle_center_y.append(i[1])
                DiaSum = DiaSum + i[2] * 2
                # draw the outer circle
                cv2.circle(self.displayImg, (i[0], i[1]), i[2], (0, 255, 0), 2)
                # draw the center of the circle
                cv2.circle(self.displayImg, (i[0], i[1]), 2, (0, 0, 255), 3)
                print('i[2]=', i[2])
            elif int(self.cols / 2) < i[0] < 1518:
                self.r_circle_center_x.append(i[0])
                circle_center_x.append(i[0])
                circle_center_y.append(i[1])
                DiaSum = DiaSum + i[2] * 2
                # draw the outer circle
                cv2.circle(self.displayImg, (i[0], i[1]), i[2], (0, 255, 0), 2)
                # draw the center of the circle
                cv2.circle(self.displayImg, (i[0], i[1]), 2, (0, 0, 255), 3)
                print('i[2]=', i[2])
            else:
                pass
            # print('self.circiels=', self.circles)
            # print('circle_center_x=', i[0])
            # print('circle_center_y=', i[1])
            #
            # print('画面中找到：', (len(self.circles[0, :])), '个孔')
            # print('画面中孔的直径之和为', self.DiaSum, '个像素')
            # self.dia = self.DiaSum / len(self.circles[0, :])
        if circle_center_x:
            self.dia = DiaSum / len(circle_center_x)
            print ('The diameter of circle is %s pixels' % self.dia)
            # self.logger.info("The diameter of the circle is %s pixels.", self.dia)
        else:
            self.dia = 1
            print ('Diameter of circle not correct, Temporary set dia = %s'% self.dia)
            # self.logger.info('Diameter of circle not correct, Temporary set dia = %s', self.dia)
        # print('孔直径的平均值=', self.dia, '个像素')
        # print('每个像素约等于', 1.5 / (self.DiaSum / len(self.circles[0, :])), 'mm. （假设孔的半径为1.5mm）')

    def groupLine(self):
        if self.lineResult:
            # 将self.lineResult按横坐标的大小依次排队
            self.lineResult.sort(key=lambda line: line[0])  # 以line的第一个元素为键值对lines排序
            self.lineGroup_1, self.lineGroup_2, self.lineGroup_3, self.lineGroup_4 = [], [], [], []

            # 0<x1<720 归入self.lineGroup_1
            # 720<=x1<1500 归入self.lineGroup_2
            # 1500<=x1<2180 归入self.lineGroup_3
            # 2180<=x1<self.cols 归入self.lineGroup_4
            for line in self.lineResult:
                for x1, y1, x2, y2 in line:
                    # cv2.line(self.frame, (x1, y1), (x2, y2), (0, 0, 255), 8)
                    if 50 < x1 < 500:
                        self.lineGroup_1.append(line[0])
                    if 500 <= x1 < 1310:
                        self.lineGroup_2.append(line[0])
                    if 1310 <= x1 < 2150:
                        self.lineGroup_3.append(line[0])
                    if 2150 <= x1 < 2560:
                        self.lineGroup_4.append(line[0])
            # 提取lineGroup_1的端点横坐标
            lineGroup_1_points = [(x1, y1) for line in self.lineGroup_1 for x1, y1, x2, y2 in [line]]  # 提取x
            lineGroup_1_points = lineGroup_1_points + [(x2, y2) for line in self.lineGroup_1 for x1, y1, x2, y2 in
                                                       [line]]
            self.lineGroup_1_x = [p[0] for p in lineGroup_1_points]
            # 提取lineGroup_2的端点横坐标
            lineGroup_2_points = [(x1, y1) for line in self.lineGroup_2 for x1, y1, x2, y2 in [line]]  # 提取x
            lineGroup_2_points = lineGroup_2_points + [(x2, y2) for line in self.lineGroup_2 for x1, y1, x2, y2 in
                                                       [line]]
            self.lineGroup_2_x = [p[0] for p in lineGroup_2_points]
            # 提取lineGroup_3的端点横坐标
            lineGroup_3_points = [(x1, y1) for line in self.lineGroup_3 for x1, y1, x2, y2 in [line]]  # 提取x
            lineGroup_3_points = lineGroup_3_points + [(x2, y2) for line in self.lineGroup_3 for x1, y1, x2, y2 in
                                                       [line]]
            self.lineGroup_3_x = [p[0] for p in lineGroup_3_points]

            # 提取lineGroup_4的端点横坐标
            lineGroup_4_points = [(x1, y1) for line in self.lineGroup_4 for x1, y1, x2, y2 in [line]]  # 提取x
            lineGroup_4_points = lineGroup_4_points + [(x2, y2) for line in self.lineGroup_4 for x1, y1, x2, y2 in
                                                         [line]]
            self.lineGroup_4_x = [p[0] for p in lineGroup_4_points]

            # 求leftGroup_1 横坐标平均值
            if self.lineGroup_1_x:  # 若列表不为空
                self.lineGroup_1_x_ave = np.mean(self.lineGroup_1_x)
            else:
                self.lineGroup_1_x_ave = 0
                print( '未找到边线一')
                # self.logger.info("Did find the first lines.")
                # eg.msgbox('未能找到时参照孔！','ERROR','OK')
            # 求lineGroup_2 横坐标平均值
            if self.lineGroup_2_x:
                self.lineGroup_2_x_ave = np.mean(self.lineGroup_2_x)
            else:
                self.lineGroup_2_x_ave = 0
                print('未找到边线二')
                # self.logger.info("Did not find second line.")
            # 求leftGroup_3横坐标平圴值
            if self.lineGroup_3_x:
                self.lineGroup_3_x_ave = np.mean(self.lineGroup_3_x)
            else:
                self.lineGroup_3_x_ave = 0
                print('未找到边线三')
                # self.logger.info("Did not find third line.")

            # 求lineGroup_4 横坐标平均值
            if self.lineGroup_4_x:
                self.lineGroup_4_x_ave = np.mean(self.lineGroup_4_x)
            else:
                self.lineGroup_4_x_ave = 0
                print('未找到边线四')
                # self.logger.info("Did not find fourth line.")
            print("<<<<<<<<<<<<<<<lineGroup_1=", self.lineGroup_1)
            print("<<<<<<<<<<<<<<<rightGroup_1_x=", self.lineGroup_1_x)
            print("<<<<<<<<<<<<<<<lineGroup_2=", self.lineGroup_2)
            print("<<<<<<<<<<<<<<<rightGroup_2_x=", self.lineGroup_2_x)
            print("<<<<<<<<<<<<<<<lineGroup_3=", self.lineGroup_3)
            print("<<<<<<<<<<<<<<<rightGroup_3_x=", self.lineGroup_3_x)
            print("<<<<<<<<<<<<<<<lineGroup_4=", self.lineGroup_4)
            print("<<<<<<<<<<<<<<<rightGroup_4_x=", self.lineGroup_4_x)
            # self.logger.info('lineGroup_1 = %s', self.lineGroup_1)
            # self.logger.info('lineGroup_1_x= %s', self.lineGroup_1_x)
            # self.logger.info('lineGroup_2 = %s', self.lineGroup_2)
            # self.logger.info('lineGroup_2_x= %s', self.lineGroup_2_x)
            # self.logger.info('lineGroup_3 = %s', self.lineGroup_3)
            # self.logger.info('lineGroup_3_x= %s', self.lineGroup_3_x)
            # self.logger.info('lineGroup_4 = %s', self.lineGroup_4)
            # self.logger.info('lineGroup_4_x= %s', self.lineGroup_4_x)
        else:

            print("<<<<<<<<<<<<<<<lineGroup_1=", self.lineGroup_1)
            print("<<<<<<<<<<<<<<<rightGroup_1_x=", self.lineGroup_1_x)
            print("<<<<<<<<<<<<<<<lineGroup_2=", self.lineGroup_2)
            print("<<<<<<<<<<<<<<<rightGroup_2_x=", self.lineGroup_2_x)
            print("<<<<<<<<<<<<<<<lineGroup_3=", self.lineGroup_3)
            print("<<<<<<<<<<<<<<<rightGroup_3_x=", self.lineGroup_3_x)
            print("<<<<<<<<<<<<<<<lineGroup_4=", self.lineGroup_4)
            print("<<<<<<<<<<<<<<<rightGroup_4_x=", self.lineGroup_4_x)

            self.lineGroup_1_x_ave = 0
            self.lineGroup_2_x_ave = 0
            self.lineGroup_3_x_ave = 0
            self.lineGroup_4_x_ave = 0
            self.lineGroup_1, self.lineGroup_2, self.lineGroup_3, self.lineGroup_4 = [], [], [], []
            return

    def fitline(self,lines,img):
        if lines:  # 判断是否为空
            group_1_points = [(x1, y1) for line in lines for x1, y1, x2, y2 in line]  # 提取x
            print("group_1_points =",group_1_points)
            group_1_points = group_1_points + [(x2, y2) for line in lines for x1, y1, x2, y2 in line]
            x = [p[0] for p in group_1_points]
            y = [p[1] for p in group_1_points]
            fit = np.polyfit(y, x, 1)  # 用一次多项式x=a*y +b拟合这些点,fit是（a,b)
            fit_fn = np.poly1d(fit)  # 生成多项式对象a*y+b
            xmin = int(fit_fn(0))  # 计算这条直线在图像中最左侧的横坐标
            xmax = int(fit_fn(img.shape[0]))  # 计算这条直线在图像中最右侧的横坐标
            cv2.line(img, (xmin, 0), (xmax, img.shape[0]), (0, 255, 0), 4)  # 画出直线
            # cv2.imshow("img_line",img)
            # cv2.waitKey(0)
            return (xmin + xmax)/2
        else:
            return 0

        # if lines: #判断是否为空
        #     group_1_points = [(x1, y1) for line in lines for x1, y1, x2, y2 in [line]]  # 提取x
        #     group_1_points = group_1_points + [(x2, y2) for line in lines for x1, y1, x2, y2 in [line]]
        #     x = [p[0] for p in group_1_points]
        #     y = [p[1] for p in group_1_points]
        #     fit = np.polyfit(y, x, 1)  # 用一次多项式x=a*y +b拟合这些点,fit是（a,b)
        #     fit_fn = np.poly1d(fit)  # 生成多项式对象a*y+b
        #     xmin = int(fit_fn(0))  # 计算这条直线在图像中最左侧的横坐标
        #     xmax = int(fit_fn(self.rows))  # 计算这条直线在图像中最右侧的横坐标
        #     cv2.line(self.displayImg, (xmin, 0), (xmax, self.rows), (255, 0, 0), 3)  # 画出直线
        #     # logger.info('Fit line %s',lines)
        #
        #     for line in lines:
        #         for x1,y1,x2,y2 in [line]:
        #             cv2.circle(self.displayImg, (x1, y1), 8, (0, 0, 255), 4)
        #             cv2.circle(self.displayImg, (x2, y2), 8, (0, 0, 255), 4)
        #             print ('lines=',lines,'\n','x=',x,'y=',y,'xmin=',xmin,'xmax=',xmax)
        #             # self.logger.info("Fit one line with points:(%s,%s),(%s,%s)",x,y,xmin,xmax)
        # else:
        #     pass

    def relay(self,comd):
        if self.ser!=None:
            try:
                self.ser.write(comd)
                print('Serial port sent data successfully')
                # self.logger.info("Send message to %",self.COM)
            except Exception as e:
                print(self.alarm)
                print ('Serial port sent data failed',self.alarm, e)
                # self.logger.info("Failed to sent message to %s",self.COM)
                self.msg += '串口数据发送失败！'
        else:
            print('Serial port sent data failed')
            # self.logger.info("Failed to sent message to %s", self.COM)
            self.msg += '串口未打开！'

    def pixel_mm(self):
        sum = 0
        print("all circle list: ", self.circle_list_0,self.circle_list_1,self.circle_list_2,self.circle_list_3)
        if self.circle_list_0 and self.circle_list_1 and self.circle_list_2 and self.circle_list_3:
            for c in self.circle_list_0:
                sum = sum + c[2]
            for c in self.circle_list_1:
                sum = sum + c[2]
            for c in self.circle_list_2:
                sum = sum + c[2]
            for c in self.circle_list_3:
                sum = sum + c[2]
            number_circle = len(self.circle_list_0)+len(self.circle_list_1) + len(self.circle_list_2) + len(self.circle_list_3)
            self.dia = sum/number_circle
            self.pixelTomm = round(CIRCLE_DIA/self.dia, 6)
            # .info('One pixel about %s mm',self.pixelTomm)
            print()
            print("sum =", sum, "number of circle =", number_circle, 'One pixel about =', self.pixelTomm, 'mm')
        else:
            self.pixelTomm = 1
        return self.pixelTomm

    def mm_pixel(self):
        self.mmToPixel= 1/self.pixel_mm()
        # self.logger.debug("1mm=%s",self.mmToPixel)

    def distCal(self):
        print("alarm",self.alarm)
        try:
            if self.calibrate:
                print("校验")
                self.pixel_mm()
                self.mm_pixel()
            else:
                print("未校验")
            if self.adjustPostive:
                print("__________________________________Postive", self.pixelTomm)
                self.pixelTomm = round(self.pixelTomm + 0.0001, 6)
                self.mmToPixel = 1/self.pixelTomm
                self.adjustPostive = False
            else:
                pass
            if self.adustNegative:
                print("__________________________________Negative",self.pixelTomm)
                self.pixelTomm = round(self.pixelTomm - 0.0001, 6)
                self.mmToPixel = 1 / self.pixelTomm
                self.adustNegative = False
            else:
                pass
            print("Before: self.pixelTomm =", self.pixelTomm, "dist_0 =", self.dist_0, "self.dist_1 =", self.dist_1,
                  "self.dist_2 =", self.dist_2,"self.dist_3 =", self.dist_3)
            self.dist_0 = round(self.dist_0 * self.pixelTomm - 1.5, 2)
            self.dist_1 = round(self.dist_1 * self.pixelTomm + 1.5, 2)
            self.dist_2 = round(self.dist_2 * self.pixelTomm - 1.5, 2)
            self.dist_3 = round(self.dist_3 * self.pixelTomm + 1.5, 2)
            # self.dist_1 = ((self.circleList_l[0][0] + (self.dia / 2)) - (
                        # self.rectList_l[0][0] + self.rectList_l[0][2])) * self.pixelTomm
            print("After: self.pixelTomm =",self.pixelTomm, "dist_0 =", self.dist_0, "self.dist_1 =", self.dist_1, "self.dist_2 =", self.dist_2, "self.dist_3 =", self.dist_3)
        except Exception as e:
            self.msg += '相机位置不对，请重新设定！'
            if self.alarm:
                self.relay(OPEN)
            else:
                self.relay(CLOSE)
            cv2.putText(self.img, "NG", (10, 280), self.font, 8, (255, 0, 0), 8, cv2.LINE_AA)
            print('相机位置不对，请重新设定！')
            # self.logger.info("相机位置不对，请重新设定！")
            return False

        print(" 检测结果",  self.dist_0, self.dist_1,self.dist_2,self.dist_3)
        if (0 < self.dist_0 < self.wid) and (0 < self.dist_3 < self.wid) and (0 < self.dist_1 < self.dist) and (0 < self.dist_2 < self.dist):
            cv2.putText(self.img, "OK", (10, 280), self.font, 8, (0, 0, 255), 8, cv2.LINE_AA)
            self.relay(CLOSE)
            print('Distance calculate OK,Relay close. Left dist out side = ', self.dist_0, 'left side middle = ', self.dist_1,
                  ' Right dist middle = ', self.dist_2, ' Right dist out side = ', self.dist_3)
            # self.logger.info("Diantance and wide are OK, left width=%s,right_width=%s,dist_1=%s,dist_2=%s",
                             # self.wid_1, self.wid_2, self.dist_1, self.dist_2)
            return True
        else:
            cv2.putText(self.img, "NG", (10, 280), self.font, 8, (255, 0, 0), 8, cv2.LINE_AA)
            if self.alarm:
                self.relay(OPEN)
            else:
                self.relay(CLOSE)
            print('Distance calculate NG,Relay open. left dist out side = ', self.dist_0, 'Left dist middle = ', self.dist_1,
                  ' Right dist middle = ', self.dist_2, ' Right dist out side = ', self.dist_3)
            # self.logger.info("Diantance or wide is/are NG, left width=%s,right_width=%s,dist_1=%s,dist_2=%s",
                             # self.wid_1, self.wid_2, self.dist_1, self.dist_2)
            return False

    def selectROI(self,img, imgList):
        self.roiList = []
        print("class IMG.selectROI() is called")
        #print ('>>>>',analysisList)
        # self.logger.info("class IMG.selectROI() is called")
        if imgList:
            for item in imgList:
                left = int(item[0])
                top = int(item[1])
                rows = int(item[2])
                cols = int(item[3])
                bottom = top + rows
                right = left + cols
                roi_img = Img()
                roi_img.setImg(img[top:bottom, left:right])
                roi_img.pos = [left, top]
                roi_img.getImageSize()
                if self.calibrate:
                    print("标定中。。。。。。。。。。。。。")
                    roi_img.bin_threshold = self.currentBinThreshold
                else:
                    print("未标定。。。。。。。。。。。。。")
                    roi_img.bin_threshold = int(item[4])
                # cv2.imshow("roi",roi_img.img)
                # cv2.waitKey(0)
                self.roiList.append(roi_img)
        else:
            pass


        # for img in self.roiList:
        #     print ("bin=", img.bin_threshold)
        #     cv2.imshow("ROI",img.img)
        #     cv2.waitKey(0)

    def analysisROI(self):
        print("static analysis called...")
        j = 0
        try:
            print("ROI Number =",len(self.roiList))
        except Exception as e:
            print("print len e", e)
        for img in self.roiList:
            blur = self.gaussianblur(img.img)
            ret, img_bin = self.threshold(blur,img.bin_threshold)
            print("img.bin_threshold =",img.bin_threshold)
            if j == 0:
                edges = cv2.Canny(blur, img.canny_min, img.canny_max)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=10, maxLineGap=10)
                lines = self.cleanLine(lines, img.img, False)
                line_x = int(self.fitline(lines, img.img))
                print("图片位置：", img.pos[0], img.pos[1])
                left = img.pos[0]
                right = left + img.cols
                top = img.pos[1]
                bottom = top + img.rows
                self.circle_list_0, self.line_list_0 = self.findFrame(img.img, img_bin)
                print("self.circle_list_0 =", self.circle_list_0, "self.line_list_0 =",self.line_list_0)
                print("231")
                if self.line_list_0:
                    if line_x < self.circle_list_0[0][0] or abs(line_x - self.line_list_0[0][0]) < 8:
                        self.dist_0 = self.line_list_0[0][0] - self.circle_list_0[0][0]
                        cv2.line(img.img, (self.line_list_0[0][0], int(img.rows/2)), (self.circle_list_0[0][0], int(img.rows/2)), (0, 0, 255),
                                 4)
                        print("123")
                    elif self.circle_list_0[0][0] < line_x and abs(line_x - self.line_list_0[0][0]) >= 8:
                        self.dist_0 = line_x - self.circle_list_0[0][0]
                        cv2.line(img.img, (line_x, int(img.rows/2)), (self.circle_list_0[0][0], int(img.rows/2)), (0, 0, 255),
                                 4)
                        print("321")
                    else:
                        self.dist_0 = 0
                        print("213")
                    print("########## error: self.circle_list_0[0][0] =", self.circle_list_0[0][0],
                              "self.line_list_0[0][0] =", self.line_list_0[0][0], "line_x=", line_x)
                else:
                    pass
                # 圈出分析区域
                cv2.rectangle(img.img, (0, 0), (img.cols, img.rows), (0, 255, 0), 4)
                # 将分析区放回原图
                self.puzzle(img.img, top, bottom, left, right)
            elif j == 1:
                edges = cv2.Canny(blur, img.canny_min, img.canny_max)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=10, maxLineGap=10)
                lines = self.cleanLine(lines, img.img, True)
                line_x = int(self.fitline(lines, img.img))
                print("图片位置：", img.pos[0], img.pos[1])
                left = img.pos[0]
                right = left + img.cols
                top = img.pos[1]
                bottom = top + img.rows
                self.circle_list_1, self.line_list_1 = self.findFrame(img.img, img_bin)
                print("Info_1: line_list =", self.line_list_1, "circle list", self.circle_list_1)
                # print("Right corner: ", self.line_list_1[0][0] + self.line_list_1[0][2], line_x)

                if self.line_list_1:
                    print("Info_2:", self.line_list_1[0][0], line_x)
                    right_corner_x = self.line_list_1[0][0] + self.line_list_1[0][2]
                    if line_x > self.circle_list_1[0][0] or abs(right_corner_x - line_x) < 8:
                        self.dist_1 = self.circle_list_1[0][0] - right_corner_x
                        cv2.line(img.img, (self.circle_list_1[0][0], int(img.rows/2)), (right_corner_x, int(img.rows/2)), (0, 0, 255),4)
                    elif line_x < self.circle_list_1[0][0] and abs(line_x - right_corner_x) >= 8:
                        self.dist_1 = self.circle_list_1[0][0] - line_x
                        cv2.line(img.img, (self.circle_list_1[0][0], int(img.rows/2)), (line_x,int(img.rows/2)), (0, 0, 255),
                                 4)
                    else:
                        self.dist_1 = 0
                else:
                    pass
                # 圈出分析区域
                cv2.rectangle(img.img, (0, 0), (img.cols, img.rows), (0, 255, 0), 4)
                # 将分析区放回原图
                self.puzzle(img.img, top, bottom, left, right)
            elif j == 2:
                edges = cv2.Canny(blur, img.canny_min, img.canny_max)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=10, maxLineGap=10)
                lines = self.cleanLine(lines, img.img, False)
                line_x = int(self.fitline(lines, img.img))
                print("图片位置：", img.pos[0], img.pos[1])
                left = img.pos[0]
                right = left + img.cols
                top = img.pos[1]
                bottom = top + img.rows
                self.circle_list_2, self.line_list_2 = self.findFrame(img.img, img_bin)
                print("Info_2: line_list =", self.line_list_2, "circle list", self.circle_list_2)
                # print("Info_2 Right corner: ", self.line_list_2[0][0], line_x)

                if self.line_list_2:
                    if line_x < self.circle_list_2[0][0] or abs(line_x - self.line_list_2[0][0]) < 8:
                        self.dist_2 = self.line_list_2[0][0] - self.circle_list_2[0][0]
                        cv2.line(img.img, (self.line_list_2[0][0], int(img.rows / 2)),
                                 (self.circle_list_2[0][0], int(img.rows / 2)), (0, 0, 255), 4)
                    elif line_x > self.circle_list_2[0][0] and abs(line_x - self.line_list_2[0][0]) > 8:
                        self.dist_2 = line_x - self.circle_list_2[0][0]
                        cv2.line(img.img, (line_x, int(img.rows / 2)),
                                 (self.circle_list_2[0][0], int(img.rows / 2)), (0, 0, 255), 4)
                    else:
                        self.dist_2 = 0
                else:
                    pass
                # 圈出分析区域
                cv2.rectangle(img.img, (0, 0), (img.cols, img.rows), (0, 255, 0), 4)
                # 将分析区放回原图
                self.puzzle(img.img, top, bottom, left, right)
            elif j == 3:
                edges = cv2.Canny(blur, img.canny_min, img.canny_max)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=10, maxLineGap=10)
                lines = self.cleanLine(lines, img.img, True)
                line_x = int(self.fitline(lines, img.img))
                print("图片位置：", img.pos[0], img.pos[1])
                left = img.pos[0]
                right = left + img.cols
                top = img.pos[1]
                bottom = top + img.rows
                self.circle_list_3, self.line_list_3 = self.findFrame(img.img, img_bin)
                print("self.circle_list_3 =", self.circle_list_3)

                if self.line_list_3:
                    print("Info_3:", self.line_list_3[0][0], line_x)
                    right_corner_x = self.line_list_3[0][0] + self.line_list_3[0][2]
                    if line_x > self.circle_list_3[0][0] or abs(right_corner_x - line_x) < 8 or line_x == 0:
                        self.dist_3 = self.circle_list_3[0][0] - right_corner_x
                        cv2.line(img.img, (self.circle_list_3[0][0], int(img.rows / 2)),
                                 (right_corner_x, int(img.rows / 2)), (0, 0, 255), 4)
                    elif line_x < self.circle_list_3[0][0] and abs(right_corner_x - line_x) > 8 and line_x != 0:
                        self.dist_3 = self.circle_list_3[0][0] - line_x
                        cv2.line(img.img, (self.circle_list_3[0][0], int(img.rows / 2)),
                                 (line_x, int(img.rows / 2)), (0, 0, 255), 4)
                else:
                    pass
                # 圈出分析区域
                cv2.rectangle(img.img, (0, 0), (img.cols-3, img.rows), (0, 255, 0), 4)
                # cv2.imshow("img.img",img.img)
                # cv2.waitKey(0)
                # 将分析区放回原图
                self.puzzle(img.img, top, bottom, left, right)

            else:
                pass
            j += 1

    def display(self):
        print("diaplay called")
        if self.displayEdage:
            #return self.img_bin
            ret, self.img_bin = self.threshold(self.img,threshold=self.currentBinThreshold)
            displayImage = self.resize(self.img_bin,self.scale)
        else:
            displayImage = self.resize(self.img,self.scale)
        # cv2.imshow("asdf",displayImage)
        # cv2.waitKey(0)
        return displayImage

    def _analysis(self,img,analysisList,imgList):
        print("class IMG.analysis() is called")
        #print ('>>>>',analysisList)
        # self.logger.info("class IMG.analysis() is called")
        # self.gauss = analysisList[0]
        # self.canny_min = analysisList[1]
        # self.canny_max = analysisList[2]
        # self.lineThreshold = analysisList[3]
        # self.circleDiaMin = analysisList[4]
        # self.circleDiaMax = analysisList[5]
        # self.circleThreshold = analysisList[6]
        # self.circelVote = analysisList [7]
        # self.circelDist = analysisList [8]
        # self.displayEdage = analysisList[9]
        # self.bin_threshold = analysisList[10]
        # self.calibrate = analysisList[11]
        self.calibrate = analysisList[0]
        self.wid = analysisList[1]
        self.dist = analysisList[2]
        self.label_height = analysisList[3]
        self.displayEdage = analysisList[4]
        self.currentBinThreshold = analysisList[5]
        self.adjustPostive = analysisList[6]
        self.adustNegative = analysisList[7]
        self.label_width = analysisList[8]
        self.alarm = analysisList[9]
        self.msg = ""
        self.setImg(img)
        self.getImageSize()
        self.scale_cal()

        if imgList:
            self.selectROI(img, imgList)
            self.analysisROI()
            self.distCal()
        else:
            pass

        displayImg = self.display()
        resultList = [self.dist_0, self.dist_1, self.dist_2, self.dist_3]
        return displayImg,resultList
        #print("比较",label_height,self.cols,self.scale)
        #self.findFrame(img)
        #self.distCal()
        #resultList = [self.wid_1, self.wid_2, self.dist_1, self.dist_2]
        msg = self.msg

     # cv2.imshow('bin',self.img_bin)
        # cv2.waitKey(0)
        # cv2.imshow('img',self.img)
        # cv2.wiatkey(0)
    def analysis(self,img,analysisList,imgList):


        try:
            displayImage = self._analysis(img,analysisList,imgList)
            return displayImage
        except Exception as e:
            print("analysis exception", e)
            if self.displayEdage:
                # return self.img_bin
                displayImage = self.resize(self.img_bin, self.scale)
                return displayImage
            else:
                displayImage = self.resize(self.img, self.scale)
                return displayImage
        finally:
            #time.sleep(1)   #速度，特意放慢
            return displayImage
            # cv2.imshow("asdf",displayImage)
            # cv2.waitKey(0)
        # finally:
        #     return displayImage

    def staticAnalysis(self,img,analysisList,imgList):
        self.calibrate = analysisList[0]
        self.wid = analysisList[1]
        self.dist = analysisList[2]
        label_height = analysisList[3]
        self.displayEdage = analysisList[4]
        self.currentBinThreshold = analysisList[5]
        self.msg = ""
        self.setImg(img)
        self.getImageSize()
        self.scale_cal()
        if imgList:
            try:
                self.selectROI(img, imgList)
            except Exception as e:
                print("Select ROI exception:", e)
            try:
                self.analysisROI()
            except Exception as e:
                print("static Analysis ROI exception:", e)
        else:
            pass
        displayImg = self.display()
        return displayImg




if __name__ == '__main__':
    img = Img()
    shift = "None"
    img.dist=11.11
    img.wid =22.22
    # 'S:,,,,2.1,1.2,1.2,2.1,,,,,,,,,,,,,2019-11-12 13:33,A:E'
    # '1,,,,5,6,7,8,,,,,,,,,,,,,2019-11-12 13:33,A:E'
    msg = "S:,,,," + str(img.dist_0) + "," + str(img.dist_1) + "," + str(img.dist_3) + "," + str(img.dist_3) \
          + "," + "," + str(img.dist) + "," + str(img.wid) + "," + ",,,,,," + str(
        timeit.default_timer()) + "," + shift + ":E"
    img.db.writeDB(msg)