from panda3d.core import Texture
from panda3d.core import GraphicsOutput
from direct.task.Task import Task

"""

This is intended to serve is a queueing system for one shot rendering to textures.

"""

def dispose(nodePath):
    def kill(n):
        for p in n.getChildren():
            kill(p)
        n.removeNode()
    kill(nodePath.getTop())

class QueueItem:
    def __init__(self, width, height, callback, getCam, callbackParams=(), getCamParams=(), cleanUpCamCall=dispose,toRam=False, texture=None):
        self.cleanUpCamCall=cleanUpCamCall
        self.width=width
        self.height=height
        self.callbackProp=callback
        self.getCamMethod=getCam
        self.getCamParams=getCamParams
        self.toRam=toRam
        self.callbackParams=callbackParams
        self.texture=texture if texture is not None else Texture()
    def callback(self,tex):
        self.callbackProp(tex,*self.callbackParams)
    def getCam(self):
        return self.getCamMethod(*self.getCamParams)
    
    
class SimpleQueueItem(QueueItem):
    """
    
    cam is passed to __init__ instead of getCam, thus, scene must be pregenerated, rather than assemblerd when needed.
    Use QueueItem instead to dynamically build the scene at the last possible moment with getCam to save space/memory or
    to spread scene assembly time out using queue.
    
    """
    def __init__(self, width, height, callback, cam, toRam=False, texture=None):
        self.cam=cam
        QueueItem.__init__(self, width, height, callback,getCam=None, toRam=toRam, texture=texture)
    def getCam(self):
        return self.cam

class Queue:
    def __init__(self):
        self.buffs={}
        self.queue=[]
        self.currentItem=None
        
        self.renderFrame=0
        
        taskMgr.add(self.processQueue,"processRenderTexQueue")
        
    def processQueue(self,task):
        self.renderFrame+=1
        
        if self.currentItem is None:
            if len(self.queue) > 0:
                # Process a queue item!
                self.currentItem=self.queue.pop(0)
                self.renderFrame=0

                self.currentBuff=self.getBuff(self.currentItem.width,self.currentItem.height)
                self.currentBuff.setActive(True)
                    
                # maybe should use RTMCopyTexture?
                mode=GraphicsOutput.RTMCopyRam if self.currentItem.toRam else GraphicsOutput.RTMBindOrCopy
                self.currentBuff.addRenderTexture(self.currentItem.texture,GraphicsOutput.RTMCopyRam)
                
                self.cam=self.currentItem.getCam()
                
                dr = self.currentBuff.makeDisplayRegion(0, 1, 0, 1)
                dr.setCamera(self.cam)

        else:
            if self.renderFrame>1:
                # Should be rendered by now
                tex = self.currentBuff.getTexture()
                self.currentBuff.setActive(False)
                self.currentBuff.clearRenderTextures()
                self.currentItem.callback(tex)
                
                self.currentItem.cleanUpCamCall(self.cam)
                del self.cam
                self.currentItem=None
        
        return Task.cont
        
    def removeBuffers(self):
        for s in self.buffs:
            base.graphicsEngine.removeWindow(self.buffs[s])
        self.buffs={}
    
    def getBuff(self,width,height):
        size=(width,height)
        
        if size in self.buffs:
            buff=self.buffs[size]
        else:
            mainWindow=base.win
            buff=mainWindow.makeTextureBuffer('QueueBuff'+str(size),width,height,Texture(),True)
            self.buffs[size]=buff
            print "saved buffer "+str(size)
            
        return buff
    
    def renderTex(self, queueItem):
        """
        
        This is where the map images are genrated.
        A render to texture process is used.
        
        
        """
        
        q=queueItem
        
        # Resolution of texture/buffer to be rendered
        buff=self.getBuff(q.width,q.height)
        
        
        buff.setActive(True)
            
        # maybe should use RTMCopyTexture?
        mode=GraphicsOutput.RTMCopyRam if q.toRam else GraphicsOutput.RTMBindOrCopy
        buff.addRenderTexture(q.texture,GraphicsOutput.RTMCopyRam)
        
        '''
        c=q.getCam()
        
        p=c.getParent()
        
        cam=base.makeCamera(buff,useCamera=c)
        
        # Fix for stupid ShowBase.makeCamera having cam.reparentTo(self.camera)
        # Remove when ShowBase is fixed
        cam.reparentTo(p)
        
        '''
        
        dr = buff.makeDisplayRegion(0, 1, 0, 1)
        dr.setCamera(q.getCam())
        
        """
        
        Here the texture is aauctually generated
        For some unknowen reason, both calls to:
        base.graphicsEngine.renderFrame() 
        are needed or there are issues when using multiple textures.
        The call to:
        altRender.prepareScene(base.win.getGsg())
        fixes this issue.
        
        
        """
        threaded=False
        def waitAFrame():
            if threaded:
                i = self.frameCount
                
                # The + 2 is used because where frameCount gets updated in the frame
                # and where this code runs in the frame
                # are not really knowen.
                while self.frameCount < i+2:
                    #print i
                    Thread.considerYield()
            else:
                base.graphicsEngine.renderFrame()
                
        
        
        # Comment out this line to cause the bug with multiple textures requireing an extra frame to
        # work properly
        #self.altRender.prepareScene(base.win.getGsg())
        
        
        
        
        waitAFrame()
        waitAFrame()
        tex = buff.getTexture()
        buff.setActive(False)
        buff.clearRenderTextures()

        
        return tex
        