#!/usr/bin/python
#__*__coding:utf-8__*__

#!/usr/bin/python
#__*__coding:utf-8__*__
import ctypes
import sys
import cv2
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import uic
from PyQt4 import QtCore
from PyQt4.QtGui import QMessageBox
import easygui as eg

import numpy as np
import timeit
import time
import queue
from pypylon import pylon
from image import Img
import os
import copy

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import logging
from logging.handlers import RotatingFileHandler
import sqlserverDB
import cProfile

FRAMENAME = '.\\2B.ui'
DIALOGNAME = '.\\dialog.ui'
FILENAME_CAM = 'test.pfs'
IMG_QUEUE = queue.Queue()

SERVERS = '10.16.0.85'
DBNAME = 'ignitions'
DBUSER = 'ignitions'
DBPWD = 'ignitions'

Ui_MainWindow, QtBaseClass = uic.loadUiType(FRAMENAME)

class MainForm(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Marian Suzhou')
        self.startFlag = False
        self.stopFlag = False
        self.pNumber = "P047706"
        self.threadList = []  # 使用列表存储新创建的线程
        self.setWindowIcon(QtGui.QIcon('marian.ICO'))
        self.setMouseTracking(True)
        self.labImg.setMouseTracking(True)
        self.pos_start = []
        self.pos_stop = []
        self.pos_xy = []
        self.QtImg = np.zeros((600,800),np.uint8)
        self.pen = QPen(Qt.black, 2, Qt.SolidLine)
        self.cut = False
        self.partROIChanged = False
        self.pNumberModified = False
        self.adjustPostive = False
        self.adjustNegative = False
        self.rectList = []
        #self.labImg.setAcceptDrops(True)

        self.labelStatus = QtGui.QLabel();
        self.labelStatus.setText(self.pNumber)
        self.labelStatus.setFixedWidth(100)
        self.statusbar.addPermanentWidget(self.labelStatus)
        self.btn_cut.setEnabled(False)
        self.btn_cutConfirm.setEnabled(False)

        self.labelMousePos = QLabel()
        self.labelMousePos.setText(self.tr(""))
        self.labelMousePos.setFixedWidth(350)
        self.statusbar.addPermanentWidget(self.labelMousePos)

        #self.sBar.addPermanentWidget(self.labelMousePos)

        self.btn_start.clicked.connect(self.btn_start_clicked)
        self.btn_stop.clicked.connect(self.btn_stop_clicked)
        self.btn_stop.clicked.connect(self.slotStopImgThread)
        self.btn_start.clicked.connect(self.slotCreateNewThread)
        # self.btn_stop.clicked.connect(self.slotStopAllThread)
        self.btn_cut.clicked.connect(self.btn_cut_clicked)
        self.btn_cutConfirm.clicked.connect(self.btn_cutConfirm_clicked)
        self.btn_save.clicked.connect(self.save)
        self.btn_adjustPostive.clicked.connect(self.slotAdjustPostive)
        self.btn_adjustNegative.clicked.connect(self.slotAdjustNegative)
        self.slider_gauss.valueChanged.connect(self.slider_gauss_changed)

        partList = ["P047706", "P047708", "P047397", "P050005", "P048189", "P047675",
                    "P045784", "P045937", "P045819", "P046226", "P049703", "P045917", "P046025",
                    "P049034", "P045508", "P037444", "P037445", "P028994", "P029760", "P050915",
                    "P037474", "P037447", "P028995", "P045222", "P037478", "P037457", "P028837",
                    "P037451", "P045212", "P037477", "P042217", "P031434", "P037476", "P033610",
                    "P037455", "P033764", "P036640", "P034395", "P040991", "P041350", "P040384",
                    "P040990", "P040799", "P030596", "P042822", "P040098", "P047722", "P047721",
                    "P049304", "P051172"]
        self.comboBox_pNumber.addItems(partList)  # 添加多个项目
        self.comboBox_pNumber.currentIndexChanged.connect(self.pNumberChnaged)

        self.wid = round(10.58 + 1, 2)
        self.dist = round(10.58 + 1, 2)
        msg = ' ' + self.pNumber + ' 料宽:' + str(self.wid) + ' 距离:' + str(self.dist)
        self.statusBar().showMessage(msg, )

        # self.actionP047722.triggered.connect(self.P047722_Clicked)
        # self.actionP047706.triggered.connect(self.P047706_Clicked)

    def slotCreateNewThread(self):
        self.startFlag = True
        self.stopFlag = False
        if self.threadList:
            pass
        else:
            threadCamera = CameraThread(len(self.threadList))
            threadCamera.dispSignal_text.connect(self.slotDisplayText)
            threadCamera.dispSignal_msg.connect(self.displayMessage)
            threadCamera.start()
            logger.info('Camera thread start.')
            self.threadList.append(threadCamera)
            threadImage = ImgThread(len(self.threadList))
            threadImage.dispSignal_text.connect(self.slotDisplayText)
            threadImage.dispSignal_img.connect(self.slotDisplayImg)
            threadImage.start()
            logger.info('Image anlysis thread start.')
            self.threadList.append(threadImage)

    def btn_start_clicked(self):
        self.startFlag = True
        self.stopFlag = False
        self.btn_cut.setEnabled(False)
        self.btn_cutConfirm.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.comboBox_pNumber.setEnabled(False)
        # self.loadPartInfo()


        logger.info('START button clicked.')
        #while self.start:

    def slotStopImgThread(self):
        pass

    def slotStopAllThread(self):
        self.stopFlag = True
        self.startFlag = False
        time.sleep(1)
        for thread in self.threadList:
            if thread.isRunning():
                #thread.stop()
                #thread.quit()
                thread.exit()
        logger.info("Exit Camera and Image thread.")
        del self.threadList[:]

    def slotDisplayText(self,val):
        self.text_info.append(val)

    def displayMessage(self,msg):
        QMessageBox.warning(self, 'Message', msg)

    def btn_stop_clicked(self):
        self.stopFlag = True
        self.startFlag = False
        self.btn_cut.setEnabled(True)
        self.btn_cutConfirm.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.comboBox_pNumber.setEnabled(True)
        self.rectList = []
        # for thread in self.threadList:
        #     if thread.isRunning():
        #         #thread.stop()
        #         #thread.quit()
        #         thread.stop()
        logger.info('STOP button clicked.')

    def btn_cut_clicked(self):
        self.pos_start = []
        self.pos_stop = []
        self.cut = True
        subImgList.clear()

        # cut_dialog = CutDialog()
        # #self.QtImg = QtGui.QPixmap.fromImage(self.QtImg)
        # #self.labImg.setPixmap(self.QtImg)
        # cut_dialog.label_cut_img.setPixmap(self.QtImg)
        # cut_dialog.show()
        # cut_dialog.exec_()

        # threadCut = CutThread(len(self.threadList))
        # threadCut.dispSignal_text.connect(self.slotDisplayText)
        # threadCut.dispSignal_img.connect(self.slotDisplayImg)
        # threadCut.start()
        # logger.info('Image anlysis thread start.')
        # self.threadList.append(threadCut)

    def btn_cutConfirm_clicked(self):
        self.cut = False
        # print (subImgList[0].pos,subImgList[0].rows,subImgList[0].cols)
        # cut_img.img = img.cutImage(subImgList[0].pos[1],subImgList[0].pos[1]+subImgList[0].rows,
                                             # subImgList[0].pos[0],subImgList[0].pos[0]+subImgList[0].cols)
        global img
        cut_img.img = img.cutImage(cut_img.pos[1],cut_img.pos[1]+cut_img.rows,cut_img.pos[0],cut_img.pos[0]+cut_img.cols)
        cut_img.gauss = self.slider_gauss.value()
        cut_img.canny_min = self.slider_cannyMin.value()
        cut_img.canny_max = self.slider_cannyMax.value()
        cut_img.bin_threshold = self.slider_binThreshold.value()
        cut_img.lineThreshold = self.slider_lineThreshold.value()
        cut_img.circleDiaMin = self.slider_circleDiaMin.value()
        cut_img.circleDiaMax = self.slider_circleDiaMax.value()
        cut_img.circleThreshold = self.slider_circleThreshold.value()
        cut_img.circleVote = 0
        cut_img.circleDist = 0
        cut_img.getImageSize()
        # cut_imgList = [cut_img.pos[0],cut_img.pos[1],cut_img.cols,cut_img.rows,cut_img.bin_threshold]
        subImgList.append(copy.deepcopy(cut_img))
        print('subImgList =',subImgList[:])

        # cut_dialog = CutDialog()
        # #self.QtImg = QtGui.QPixmap.fromImage(self.QtImg)
        # #self.labImg.setPixmap(self.QtImg)
        # img_rgb = cv2.cvtColor(subImgList[0].img, cv2.COLOR_RGB2BGRA)
        # lab_img = QtGui.QImage(img_rgb.data, img_rgb.shape[1], img_rgb.shape[0],
        #                           QtGui.QImage.Format_RGB32)
        # lab_img = QtGui.QPixmap.fromImage(lab_img)
        # cut_dialog.label_cut_img.setPixmap(lab_img)
        # cut_dialog.show()
        # cut_dialog.exec_()

    def save(self):
        fileStr = self.pNumber
        fileName = fileStr + '.txt'
        if not os.path.exists(fileName):
            partsFile = open(fileName, 'w')
            if subImgList:
                for img in subImgList:
                    partInfo = str(img.pos[0]) + "," + str(img.pos[1]) + "," + str(img.rows) + "," + str(img.cols) + "," \
                               + str(img.bin_threshold) + ','+ str(img.gauss) + "," + str(img.canny_min) + "," \
                               + str(img.canny_max) + "," + str(img.lineThreshold) + '\n'
                    partsFile.write(partInfo)
                    print("first time part info =", partInfo, "img.bin_threshold=", img.bin_threshold)

            partsFile.close()
        else:
            partsFile = open(fileName, 'w')
            if subImgList:
                for img in subImgList:
                    partInfo = str(img.pos[0]) + "," + str(img.pos[1]) + "," + str(img.rows) + "," + str(img.cols) + "," \
                               + str(img.bin_threshold) + ','+ str(img.gauss) + "," + str(img.canny_min) + "," \
                               + str(img.canny_max) + "," + str(img.lineThreshold) + '\n'
                    partsFile.write(partInfo)
                    print("part info =", partInfo, "img.bin_threshold=", img.bin_threshold)
            print("already existed.")
        self.partROIChanged = True
        # subImgList.clear()
        print("clicked save",self.partROIChanged)

    def slotAdjustPostive(self):
        self.adjustPostive = True

    def slotAdjustNegative(self):
        self.adjustNegative = True

    def slider_gauss_changed(self):
        #print(self.slider_gauss.value())
        pass

    def slotDisplayImg(self,img):
        # img = cv2.imread('a.jpg')
        # if self.img is None:
        #     return None
        #将图片转成BGRA模式
        self.img_rgb = cv2.cvtColor(img,cv2.COLOR_RGB2BGRA)
        self.QtImg = QtGui.QImage(self.img_rgb.data, self.img_rgb.shape[1], self.img_rgb.shape[0],
                                      QtGui.QImage.Format_RGB32)

        #改变控件大小，以适应图片大小
        #self.labImg.resize(QtCore.QSize(self.img_rgb.shape[1],self.img_rgb.shape[0]))
        #改变图片大小，以适应控件大小,前两个参数为缩放之后图片的宽和高，第三个参数的作用是保持长宽比例不变
        # self.QtImg = self.QtImg.scaledToWidth(1100)
        #self.QtImg = self.QtImg.scaledToHeight(521)
        # 显示图片到label中
        self.QtImg = QtGui.QPixmap.fromImage(self.QtImg)
        self.labImg.setPixmap(self.QtImg)

    def camXY_winXY(self,camRow,camCol):
        #print (self.labImg.x())
        rate = self.threadList[1].img.cols/self.labImg.width() #1100为labImg的宽度
        winCol = camCol * self.threadList[1].imgScale + 2  # 2为控件横坐标相对窗口位置
        winRow = (self.labImg.height()-(self.threadList[1].img.rows * self.threadList[1].imgScale))/2 \
                 + camRow * self.threadList[1].imgScale + 25  #521为窗口高度，25为控件纵座标相对窗口位置
        pos = [winRow,winCol]
        return pos

    def winXY_camXY(self, winCol, winRow):
        camCol = (winCol - 10) / img.scale
        try:
            camRow = (winRow - 30) / img.scale - (self.labImg.height() / img.scale - img.rows) / 2
        except Exception as e:
            print("Info_3:", e)
        print("window  窗体中 img.scale =", img.scale)
                 #- (self.labImg.height() / img.scale - img.rows) / 2
        pos = [int(camCol), int(camRow)]
        return pos

    def winXY_LabXY(self,winCol,winRow):
        print ((self.labImg.height() - img.cols * img.scale)/2)
        lab_row = winRow - ((self.labImg.height() - img.rows * img.scale)/2)-30
        lab_col = winCol-10
        pos = [int(lab_col),int(lab_row)]
        return pos

    def mousePressEvent(self, event):
        self.pos_start = (event.x(), event.y())
        pos = self.winXY_camXY(self.pos_start[0], self.pos_start[1])
        cut_img.pos = pos

    def mouseReleaseEvent(self, e):
        # self.adjustPostive = False
        # self.adjustNegative = False
        if e.button() == Qt.LeftButton:
            self.pos_stop = (e.x(),e.y())
            img_pos_stop = self.winXY_camXY(self.pos_stop[0],self.pos_stop[1])
            cut_img.cols = img_pos_stop[0] - cut_img.pos[0]
            cut_img.rows = img_pos_stop[1] - cut_img.pos[1]
            painter = QPainter(self.QtImg)
            painter.setPen(self.pen)
            pos_start = self.winXY_LabXY(self.pos_start[0], self.pos_start[1])
            pos_stop = self.winXY_LabXY(self.pos_stop[0], self.pos_stop[1])
            # 0 用来占位threshold,否则后面计算时会产生list out of range 错误
            self.rectList.append([cut_img.pos[0], cut_img.pos[1],cut_img.rows, cut_img.cols,0])
            print("self.rectList===========",self.rectList)
            painter.drawRect(pos_start[0], pos_start[1],pos_stop[0]-pos_start[0], pos_stop[1]-pos_start[1])
            self.labImg.setPixmap(self.QtImg)
            print("label剪切区域：", pos_start, pos_stop)
        elif e.button() == Qt.RightButton:
            pass
        elif e.button() == Qt.MidButton:
            pass

    def mouseMoveEvent(self, event):
        #QMouseEvent
        try:
            pos = self.winXY_camXY(event.x(),event.y())
        except Exception as e:
            print("mouseMoveEvent exception:",e)
        self.labelMousePos.setText("相机坐标：(" + str(pos[0]) + "," + str(pos[1]) + ")"+
                                   "； 位图坐标："+"("+str(event.x()-30) + "," + str(event.y()-10) + ")")
        # pos_tmp = (event.pos().x(), event.pos().y())
        # self.pos_xy.append(pos_tmp)
        # painter = QPainter(self.QtImg)
        # painter.setPen(self.pen)
        # if len(self.pos_xy) > 1:
        #     point_start = self.pos_xy[0]
        #     #for pos_tmp in self.pos_xy:
        #     print(point_start[0], point_start[1], pos_tmp[0], pos_tmp[1])
        #         #painter.drawLine(point_start[0], point_start[1], pos_tmp[0], pos_tmp[1])
        #     painter.drawRect(point_start[0], point_start[1], pos_tmp[0], pos_tmp[1])
        #         #point_start = pos_tmp
        # print(pos_tmp)
        # self.labImg.setPixmap(self.QtImg)

    def closeEvent(self,Event):
        self.slotStopAllThread()
        # if cam1.camera!=None:
        #     cam1.camera.StopGrabbing()
        #     cam1.camera.Close()
        #     logger.info("Close the window, Stop grab, and close camera")
        # else:
        #     pass
        quit()
        logger.info("'Quit by click 'X' icon.")

    def pNumberChnaged(self):
        self.pNumberModified = True
        if self.comboBox_pNumber.currentText() == 'P047706':
            self.pNumber = 'P047706'
            self.wid = round(10.58 + 1, 2)
            self.dist = round(10.58 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047706 selected.")
        if self.comboBox_pNumber.currentText() == 'P047708':
            self.pNumber = 'P047708'
            self.wid = round(20.38 + 1, 2)
            self.dist = round(13.39 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047708 selected.")
        if self.comboBox_pNumber.currentText() == 'P047397':
            self.pNumber = 'P047397'
            self.wid = round(6.08 + 1, 2)
            self.dist = round(6.08 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047397 selected.")
        if self.comboBox_pNumber.currentText() == 'P050005':
            self.pNumber = 'P050005'
            self.wid = round(10.25 + 1, 2)
            self.dist = round(10.25 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P050005 selected")
        """
        未找到该产品参数
        """
        if self.comboBox_pNumber.currentText() == 'P048189':
            self.pNumber = 'P048189'
            self.wid = round(46.99-1, 2)
            self.dist = round(9.06+1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P048189 selected.")
        if self.comboBox_pNumber.currentText() == 'P047675':
            self.pNumber = 'P047675'
            self.wid = round(8.15 + 1, 2)
            self.dist = round(4.34 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047675 selected")
        if self.comboBox_pNumber.currentText() == 'P045784':
            self.pNumber = 'P045784'
            self.wid = round(6.8 + 1, 2)
            self.dist = round(9.5 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045784 selected.")
        if self.comboBox_pNumber.currentText() == 'P045937':
            self.pNumber = 'P045937'
            self.wid = round(2.8 + 1, 2)
            self.dist = round(6.73 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045937 selected.")
        if self.comboBox_pNumber.currentText() == 'P045819':
            self.pNumber = 'P045819'
            self.wid = round(3.5 + 1, 2)
            self.dist = round(6.4 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045819 selected.")
        if self.comboBox_pNumber.currentText() == 'P046226':
            self.pNumber = 'P046226'
            self.wid = round(11.75 + 1, 2)
            self.dist = round(11.75 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P046226 selected.")
        if self.comboBox_pNumber.currentText() == 'P049703':
            self.pNumber = 'P049703'
            self.wid = round(6.71 + 1, 2)
            self.dist = round(6.71 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P049703 selected.")
        if self.comboBox_pNumber.currentText() == 'P045917':
            self.pNumber = 'P045917'
            self.wid = round(17.06 + 1, 2)
            self.dist = round(12.49 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045917 selected.")
        if self.comboBox_pNumber.currentText() == 'P046025':
            self.pNumber = 'P046025'
            self.wid = round(33.64 + 1, 2)
            self.dist = round(31.36 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P046025 selected")
        """
        未找到该产品参数
        """
        if self.comboBox_pNumber.currentText() == 'P049034':
            self.pNumber = "P049034"
            self.wid = round(16.00 - 0.5, 2)
            self.dist = round(31.56 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P049034 selected.")
        if self.comboBox_pNumber.currentText() == 'P045508':
            self.pNumber = 'P045508'
            self.wid = round(20.06 + 1, 2)
            self.dist = round(15.49 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045508 selected.")
        ######################################################################################
        if self.comboBox_pNumber.currentText() == 'P037444':
            self.pNumber = 'P037444'
            self.wid = round(7.95 + 1, 2)
            self.dist = round(7.95 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037444 selected.")
        if self.comboBox_pNumber.currentText() == 'P037445':
            self.pNumber = 'P037445'
            self.wid = round(7.29 + 1, 2)
            self.dist = round(7.29 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037445 selected.")
        if self.comboBox_pNumber.currentText() == 'P028994':
            self.pNumber = 'P028994'
            self.wid = round(9.58 + 1, 2)
            self.dist = round(9.58 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P028994 selected.")
        if self.comboBox_pNumber.currentText() == 'P029760':
            self.pNumber = 'P029760'
            self.wid = round(9.58 + 1, 2)
            self.dist = round(9.58 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P029760 selected.")
        if self.comboBox_pNumber.currentText() == 'P050915':
            self.pNumber = 'P050915'
            self.wid = round(6.18 + 1, 2)
            self.dist = round(6.18 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P050915 selected.")
        if self.comboBox_pNumber.currentText() == 'P037474':
            self.pNumber = 'P037474'
            self.wid = round(6.69 + 1, 2)
            self.dist = round(6.69 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037474 selected.")
        if self.comboBox_pNumber.currentText() == 'P037447':
            self.pNumber = 'P037447'
            self.wid = round(7.36 + 1, 2)
            self.dist = round(7.36 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037447 selected.")
        if self.comboBox_pNumber.currentText() == 'P028995':
            self.pNumber = 'P028995'
            self.wid = round(6.25 + 1, 2)
            self.dist = round(6.25 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P028995 selected.")
        if self.comboBox_pNumber.currentText() == 'P045222':
            self.pNumber = 'P045222'
            self.wid = round(5.1 + 1, 2)
            self.dist = round(5.1 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P45222 selected.")
        if self.comboBox_pNumber.currentText() == 'P037478':
            self.pNumber = 'P037478'
            self.wid = round(7.29 + 1, 2)
            self.dist = round(7.29 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037478 selected.")
        if self.comboBox_pNumber.currentText() == 'P037457':
            self.pNumber = 'P037457'
            self.wid = round(10.625 + 1, 2)
            self.dist = round(10.525 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037457 selected.")
        if self.comboBox_pNumber.currentText() == 'P028837':
            self.pNumber = 'P028837'
            self.wid = round(7.5 + 1, 2)
            self.dist = round(7.5 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P028837 selected.")
        if self.comboBox_pNumber.currentText() == 'P028837':
            self.pNumber = 'P028837'
            self.wid = round(7.5 + 1, 2)
            self.dist = round(7.5 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P028837 selected.")
        if self.comboBox_pNumber.currentText() == 'P037451':
            self.pNumber = 'P037451'
            self.wid = round(7.975 + 1, 2)
            self.dist = round(7.975 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037451 selected.")
        if self.comboBox_pNumber.currentText() == 'P045212':
            self.pNumber = 'P045212'
            self.wid = round(6.19 + 1, 2)
            self.dist = round(6.19 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P045212 selected.")
        if self.comboBox_pNumber.currentText() == 'P037477':
            self.pNumber = 'P037477'
            self.wid = round(6.49 + 1, 2)
            self.dist = round(6.49 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037477 selected.")
        if self.comboBox_pNumber.currentText() == 'P042217':
            self.pNumber = 'P042217'
            self.wid = round(10.55 + 1, 2)
            self.dist = round(10.55 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P042217 selected.")
        if self.comboBox_pNumber.currentText() == 'P042217':
            self.pNumber = 'P042217'
            self.wid = round(10.55 + 1, 2)
            self.dist = round(10.55 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P042217 selected.")
        if self.comboBox_pNumber.currentText() == 'P031434':
            self.pNumber = 'P031434'
            self.wid = round(4.18 + 1, 2)
            self.dist = round(4.18 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P031434 selected.")
        if self.comboBox_pNumber.currentText() == 'P037476':
            self.pNumber = 'P037476'
            self.wid = round(5.7 + 1, 2)
            self.dist = round(5.7 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037476 selected.")
        if self.comboBox_pNumber.currentText() == 'P033610':
            self.pNumber = 'P033610'
            self.wid = round(5.05 + 1, 2)
            self.dist = round(5.05 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P033610 selected.")
        if self.comboBox_pNumber.currentText() == 'P037455':
            self.pNumber = 'P037455'
            self.wid = round(5.645 + 1, 2)
            self.dist = round(5.645 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P037455 selected.")
        if self.comboBox_pNumber.currentText() == 'P033764':
            self.pNumber = 'P033764'
            self.wid = round(6.92 + 1, 2)
            self.dist = round(7.83 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P033764 selected.")
        if self.comboBox_pNumber.currentText() == 'P036640':
            self.pNumber = 'P036640'
            self.wid = round(8.33 + 1, 2)
            self.dist = round(8.33 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P033640 selected.")
        if self.comboBox_pNumber.currentText() == 'P034395':
            self.pNumber = 'P034395'
            self.wid = round(7.39 + 1, 2)
            self.dist = round(7.39 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P034395 selected.")
        if self.comboBox_pNumber.currentText() == 'P040991':
            self.pNumber = 'P040991'
            self.wid = round(3.24 + 1, 2)
            self.dist = round(4.72 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P040991 selected.")
        if self.comboBox_pNumber.currentText() == 'P041350':
            self.pNumber = 'P041350'
            self.wid = round(7.56 + 1, 2)
            self.dist = round(7.56 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P041350 selected.")
        if self.comboBox_pNumber.currentText() == 'P040384':
            self.pNumber = 'P040384'
            self.wid = round(17.84 + 1, 2)
            self.dist = round(10.86 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P040384 selected.")
        if self.comboBox_pNumber.currentText() == 'P040990':
            self.pNumber = 'P040990'
            self.wid = round(5.8 + 1, 2)
            self.dist = round(11.24 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P040990 selected.")
        if self.comboBox_pNumber.currentText() == 'P040799':
            self.pNumber = 'P040799'
            self.wid = round(10.39 + 1, 2)
            self.dist = round(10.39 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P040799 selected.")
        if self.comboBox_pNumber.currentText() == 'P039596':
            self.pNumber = 'P039596'
            self.wid = round(6.92 + 1, 2)
            self.dist = round(7.83 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P039596 selected.")
        if self.comboBox_pNumber.currentText() == 'P042822':
            self.pNumber = 'P042822'
            self.wid = round(8.34 + 1, 2)
            self.dist = round(8.34 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P042822 selected.")
        if self.comboBox_pNumber.currentText() == 'P040098':
            self.pNumber = 'P040098'
            self.wid = round(7.25 + 1, 2)
            self.dist = round(7.25 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P040098 selected.")
        if self.comboBox_pNumber.currentText() == 'P047722':
            self.pNumber = 'P047722'
            self.wid = round(3.24 + 1, 2)
            self.dist = round(4.72 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047722 selected.")
        if self.comboBox_pNumber.currentText() == 'P047706':
            self.pNumber = 'P047706'
            self.wid = round(10.58 + 1, 2)
            self.dist = round(10.58 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047706 selected.")
        if self.comboBox_pNumber.currentText() == 'P047721':
            self.pNumber = 'P047721'
            self.wid = round(6.65 + 1, 2)
            self.dist = round(14.2 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P047721 selected.")
        if self.comboBox_pNumber.currentText() == 'P049304':
            self.pNumber = 'P049304'
            self.wid = round(31.19 + 1, 2)
            self.dist = round(31.56 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P049304 selected.")
        if self.comboBox_pNumber.currentText() == 'P051172':
            self.pNumber = 'P051172'
            self.wid = round(9.06 + 1, 2)
            self.dist = round(9.06 + 1, 2)
            msg = ' ' + self.pNumber + ' 外边间距:' + str(self.wid) + ' 内边间距:' + str(self.dist)
            self.statusBar().showMessage(msg, )
            logger.info("P051172 selected.")



Ui_Dialog, QtBaseClass = uic.loadUiType(DIALOGNAME)
class CutDialog(QtGui.QDialog, Ui_Dialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        #QtGui.QWidget.__init__(self)
        Ui_Dialog.__init__(self)
        self.setupUi(self)


class CameraThread(QtCore.QThread):
    dispSignal_text = QtCore.pyqtSignal(str)
    dispSignal_msg = QtCore.pyqtSignal(str)
    #dispSignal_img =QtCore.pyqtSignal(np.ndarray)

    def __init__(self,number = 0, parent =None):
        super(CameraThread,self).__init__(parent)
        self.number = number
        self.name = '相机拍摄'
        self.keepRunning = True
        print("name==", self.name)
        try:
            self.cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.converter = pylon.ImageFormatConverter()
            # converting to opencv bgr format
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            # 打开相机
            self.cam.Open()
            # 加载相机配制
            pylon.FeaturePersistence.Load(FILENAME_CAM, self.cam.GetNodeMap(), True)
            # 开始Grab
            self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logger.info("Open camera successfully, and start grab...")
        except Exception as e:
            self.cam = None
            print("camera exception", e)
            logger.info("Failed to open camera. Error code ==> %s", e)

    def stop(self):
        self.keepRunning = False

    def run(self):
        id = int(self.currentThreadId())
        i = 0
        while self.keepRunning:
            print("window.stopFlag =",window.stopFlag)
            if self.cam != None:
                start = timeit.default_timer()
                i = i + 1
                try:
                    retriveResult = self.cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                except Exception as e:
                    print("retrive Result exception",e)
                    logger.info("Failed retrive photo, photo No.%s", i)
                    self.dispSignal_msg.emit('相机状态异常！')
                if retriveResult.GrabSucceeded():
                    images = self.converter.Convert(retriveResult)
                    image = images.GetArray()
                    img.setImg(image)
                    #print("...................",img)
                    IMG_QUEUE.put(img.img)  # 容器添加照片
                    # 当拍完一张照片后就给处理程序发一个信号，表示拍完了，让它处理
                    #print('produce %s 已经拍好了第%s张照片' % i)
                    end = timeit.default_timer()
                    duration = end - start
                    self.dispSignal_text.emit('--> %s 线程号= %d,  拍摄第 %d 张照片, 用时: %.2f 秒' % (self.name, id, i, duration))
                    IMG_QUEUE.join()  # 等待处理信号

                #self.dispSignal_img.emit(self.cam_img)
                #self.msleep(1000)
                else:
                    logger.info("Failed retrive photo, photo No.%s", i)
                retriveResult.Release()
            else:
                print("self.cam",self.cam)
                self.dispSignal_text.emit('%s ID= %d, 相机异常，请检查相机状态！' % (self.name, id))
                logger.info("Camera status abnormal, please checkit.")
                #print (window.slider_gauss.value())
                break
        self.keepRunning = True


class ImgThread(QtCore.QThread):
    dispSignal_text = QtCore.pyqtSignal(str)
    dispSignal_img =QtCore.pyqtSignal(np.ndarray)

    def __init__(self,number = 0, parent =None):
        super(ImgThread,self).__init__(parent)
        self.number = number
        self.name = '图片分析'
        self.keepRunning = True
        self.imgScale = 1
        self.imgList = []
        self.staticImg = np.zeros((600, 800), np.uint8)
        self.loadPartInfo()



    def stop(self):
        self.keepRunning = False

    def run(self):
        id = int(self.currentThreadId())
        i = 0
        while self.keepRunning:
            calibrate = window.checkBox_cal.isChecked()
            wid_material = window.wid
            dist_material = window.dist
            display = window.checkBox_edage.isChecked()
            adjustPostive = window.adjustPostive
            window.adjustPostive = False
            adjustNegative = window.adjustNegative
            window.adjustNegative = False
            alarm = window.checkBox_alarm.isChecked()
            currentBinThreshold = window.slider_binThreshold.value()
            analysisList = [calibrate, wid_material, dist_material, window.labImg.height(), display,
                            currentBinThreshold, adjustPostive, adjustNegative,window.labImg.width(),alarm]
            if window.stopFlag:
                staticImage = image.copy()
                self.imgList = window.rectList
                print("...............", window.rectList, ">>>>>>>>>", self.imgList)
                try:
                    displayImg = img.staticAnalysis(staticImage, analysisList, self.imgList)
                    # img.scale = round(window.labImg.width() / img.cols, 2)
                except Exception as e:
                    print("window call static analysis exception =", e)
                    resultList = [0, 0, 0, 0]
                # print("....................................")
                # cv2.imshow("imshow",displayImg)
                # cv2.waitKey(0)
                self.dispSignal_img.emit(displayImg)
                if calibrate:
                    pass
                else:
                    pass
            else:
                print("window.partROIChanged =",window.partROIChanged)
                if window.partROIChanged or window.pNumberModified:
                    try:
                        self.loadPartInfo()
                        window.partROIChanged = False
                        window.pNumberModified = False
                    except Exception as e:
                        print("load part information exception", e)
                else:
                    if self.imgList:
                        pass
                    else:
                        self.loadPartInfo()
                    # pass
                start = timeit.default_timer()
                i = i + 1
                p = cProfile.Profile()
                p.enable() #开始采集
                image = IMG_QUEUE.get()  # 取图片，处理图片
                imageCopy = image.copy()
                try:
                    displayImg,resultList = img.analysis(imageCopy,analysisList,self.imgList)
                    # img.scale = round(window.labImg.width() / img.cols, 2)
                    msg = " "
                except Exception as e:
                    print("Image call Img class analysis function exception:", e)
                    resultList = [0, 0, 0, 0]
                    msg = str(resultList[0]) + "," + str(resultList[1])+"," + str(resultList[2])+"," + str(resultList[3])
                    # self.writeDB(msg)
                    displayImg = img.resize(imageCopy, img.scale)
                    msg = '图形有误！'

                # print('\033[32;1m图形处理线程 %s已经把第%s张图片处理了...\033[0m' % (name, count))
                end = timeit.default_timer()
                duration = end - start
                self.dispSignal_text.emit('==> %s 线程号 = %s, 检查第 %d 张图片, 用时: %0.2f 秒,%s '
                                           '\n左侧间距A %0.2f mm \n左侧间距B %.2f mm \n右侧间距B %.2f mm \n右侧间距A %.2f mm'
                                           % (self.name, id, i, duration, msg, resultList[0], resultList[1], resultList[2],
                                              resultList[3]))
                # cv2.imshow("img",displayImg)
                # cv2.waitKey(0)
                self.dispSignal_img.emit(displayImg)
                if resultList[0] > window.dist or resultList[3] > window.dist or resultList[1] > window.wid or resultList[2]>window.wid:
                    msg = str(resultList[0]) + "," + str(resultList[1]) + "," + str(resultList[2])+","+str(resultList[3])
                    # self.writeDB(msg)
                    pass
                else:
                    pass
                IMG_QUEUE.task_done()
                p.disable()
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                p.print_stats(sort = "tottime")
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                # self.msleep(1000)
        self.keepRunning = True

    def loadPartInfo(self):
        self.imgList = []
        print("开始加载》》》》",self.imgList)
        name = window.pNumber
        fileName = name + '.txt'
        # print("fileName=", fileName)
        if os.path.exists(fileName):
            partsFile = open(fileName, 'r')
            # for line in partsFile.readlines()
            lines = partsFile.readlines()
            # print("lines =", lines)
            for line in lines:
                d = line.strip("\n")
                # print(d)
                s = d.split(',')
                self.imgList.append(s)
                print("加载完成： self.imgList =", self.imgList)

                # print (s)
            partsFile.close()
        else:
            print("Does exit")

    def writeDB(self,msg):
        s = False
        while s != True or choice==None:
            choice = eg.buttonbox(msg='异常原因？', title='异常', choices=('误判', '接头', '材料跑偏'))
            s = eg.ynbox('你的选择是：' + str(choice), "确认？", ('是', '否'))
            if s == True and choice !=None:
                print("yes", s, choice)
                shift = "None"
                # 'S:,,,,2.1,1.2,1.2,2.1,,,,,,,,,,,,,2019-11-12 13:33,A:E'
                # '1,,,,5,6,7,8,,,,,,,,,,,,,2019-11-12 13:33,A:E'
                message = "S:,,,," + msg + "," + str(window.dist) + "," + str(
                    window.wid) + "," + choice + "," + ",,,,,,,,,,,," + str(timeit.default_timer())\
                + "," + shift + ":E"
                db.writeDB(message)
            else:
                pass



# class CutThread(QtCore.QThread):
#     dispSignal_text = QtCore.pyqtSignal(str)
#     dispSignal_img =QtCore.pyqtSignal(np.ndarray)
#     def __init__(self,number = 0, parent =None):
#         super(CutThread,self).__init__(parent)
#         self.number = number
#         self.name = '图片剪切'
#         self.keepRunning = True
#         self.imgScale = 1
#     def stop(self):
#         self.keepRunning = False
#         print ("Stop function in image analysis thread called")
#     def run(self):
#         id = int(self.currentThreadId())
#         i = 0
#         while self.keepRunning:
#             #print('%s 正在运行',name )
#             gauss = window.slider_gauss.value()
#             canny_min = window.slider_cannyMin.value()
#             canny_max = window.slider_cannyMax.value()
#             lineThreshold = window.slider_lineThreshold.value()
#             circleDiaMin = window.slider_circleDiaMin.value()
#             circleDiaMax = window.slider_circleDiaMax.value()
#             circleThreshold = window.slider_circleThreshold.value()
#             circelVote = window.slider_circleVote.value()
#             circleDist = window.slider_circleDist.value()
#             displayEdage = window.checkBox_edage.isChecked()
#             bin_threshold = window.slider_binThreshold.value()
#             calibrate = window.checkBox_cal.isChecked()
#             analysisList = [gauss,canny_min,canny_max,lineThreshold,circleDiaMin,circleDiaMax,circleThreshold,
#                             circelVote,circleDist,displayEdage,bin_threshold,calibrate]
#             self.cut_img_1 = Img()
#             self.cut_img.img = window.threadList[0].cam_img
#             try:
#                 img, resultList, msg = self.cut_img.selectROI(self.cut_img.img, analysisList)
#                 self.imgScale = round(window.labImg.width() / self.cut_img.img.shape[1], 2)
#                 resultImg = self.cut_img.resize(img, self.imgScale)
#             except Exception as e:
#                 self.imgScale = round(window.labImg.width() / self.cut_img.img.shape[1], 2)
#                 print('........',self.imgScale)
#                 resultImg = self.cut_img.resize(window.threadList[0].cam_img, self.imgScale)
#                 resultList = [0, 0, 0, 0]
#                 msg = '图形有误！'
#             self.dispSignal_text.emit('==> %s 线程号 = %s, 检查第 %d 张图片, 用于: %0.2f 秒,'
#                                       '左侧料宽 %0.2f mm,右侧料宽 %.2f mm,左侧距离 %.2f mm,右侧距离 %.2f mm %s'
#                                       % (self.name, id, i, 0.00, resultList[0], resultList[1], resultList[2],
#                                          resultList[3], msg))
#             self.dispSignal_img.emit(resultImg)
#             # self.msleep(1000)
#         self.keepRunning = True




# logging information
logger = logging.getLogger("mainApp")
logger.setLevel(logging.DEBUG)

# create find handler
# 每隔 1小时 划分一个日志文件，interval 是时间间隔，备份文件为 10 个
handler = logging.handlers.TimedRotatingFileHandler("log.txt", when="H", interval=1, backupCount=36)
# 定义一个RotatingFileHandler，最多备份3个日志文件，每个日志文件最大10*1K
handler = RotatingFileHandler('log.txt', maxBytes=50 * 1024, backupCount=100)
handler.setLevel(logging.DEBUG) #实测在此起作用
# create a logging format
formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(thread)d-%(message)s')
handler.setFormatter(formatter)

# add the handlders to logger
logger.addHandler(handler)


# class Log(logging):
#     logging.__init__()
#     def __init__(self,name):
#         # logging information
#         self.logger = logging.getLogger(name)
#         self.logger.setLevel(logging.DEBUG)
#
#         # create find handler
#         # 每隔 1小时 划分一个日志文件，interval 是时间间隔，备份文件为 10 个
#         self.handler = logging.handlers.TimedRotatingFileHandler("log.txt", when="H", interval=1, backupCount=36)
#         # 定义一个RotatingFileHandler，最多备份3个日志文件，每个日志文件最大10*1K
#         # self.handler = RotatingFileHandler('log.txt', maxBytes=50 * 1024, backupCount=100)
#         self.handler.setLevel(logging.INFO)
#
#         # create a logging format
#         formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(thread)d-%(message)s')
#         self.handler.setFormatter(formatter)
#
#         # add the handlders to logger
#         self.logger.addHandler(self.handler)



if __name__ == '__main__':
    img = Img()
    cut_img = Img()
    subImgList = []
    db = sqlserverDB.DBHelper(server=SERVERS, username=DBUSER, password=DBPWD, database=DBNAME)

    app = QtGui.QApplication(sys.argv)
    window = MainForm()
    window.showMaximized()
    window.show()
    sys.exit(app.exec_())




