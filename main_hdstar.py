from __future__ import division
import time
import os
import subprocess
import multiprocessing
import resource
from math import isinf, sqrt
import numpy as np
import matplotlib.pyplot as plt
import config_user as gl
import config_program
import all_functions as fcn



if gl.testingMode:
    reload(gl)
    reload(config_program)
    reload(fcn)



"""
USER CONFIGURATION
    use config_user.py to modify user inputs
"""


"""
PROGRAM CONFIGURATION
    done in config_program.py
    creating local copies of constants here
"""

sizeX, sizeY, sizeZ, cX, cY, cZ = gl.sizeX, gl.sizeY, gl.sizeZ, gl.cX, gl.cY, gl.cZ

searchRadius, useMovingGoals = gl.searchRadius, gl.useMovingGoals
makeRandObs, makeFigure, makeMovie, numlevels = gl.makeRandObs, gl.makeFigure, gl.makeMovie, gl.numlevels

minObs, maxObs, maxPercent, seedDyn, seedStatic = gl.minObs, gl.maxObs, gl.maxPercent, gl.seedDyn, gl.seedStatic
initX, initY, initZ, T, rXdim, rYdim, rZdim = gl.initX, gl.initY, gl.initZ, gl.T, gl.rXdim, gl.rYdim, gl.rZdim
rXstart, rYstart, rZstart = gl.rXstart, gl.rYstart, gl.rZstart
refinementDistance = gl.refinementDistance

tic = time.time()
if makeMovie:   frames = []



""" Setup abstract levels """
L = fcn.setupLevels()
time_findPath = []
total_cost = 0
path = [gl.start]


#numlevels = 0
""" Begin main algorithm """
for idx in xrange(0, gl.numGoals):                      # for each goal
    xNew, yNew, zNew = gl.start                         # get current location
    fcn.searchAndUpdate(xNew,yNew,zNew)                 # search for obstacles

    while gl.start != gl.goal:

        """ Compute path, smooth it, make a spline, and divide into a series of adjacent points to follow """
        tic1 = time.clock()    # start timer

        path = fcn.findPath(L)
        path = fcn.postSmoothPath(path)
        path = fcn.CatmullRomSpline(path)
        path = fcn.simulateUAVmovement(path)

        findPathTime = time.clock() - tic1  # end timer

        time_findPath.append(findPathTime)  # record time
        if gl.stepCount == 1:
            initialFindPathTime = findPathTime

        xOrig, yOrig, zOrig = gl.start     # to identify when leaving refinement region
        dfs = 0                             # distance from start, used to identify when path needs to be updated
        goalMoved = False                   # indicates whether or not the goal has moved
        validPath = True                    # indicates whether or not path being followed is still valid

        while not goalMoved and validPath and gl.start != gl.goal and path:

            # 4. Follow those points until path is invalidated or we reach end of refinement region
            for point in path:

                # Save current position, then move to next point
                xOld, yOld, zOld = xNew, yNew, zNew
                xNew, yNew, zNew = path.pop()
                oldstart = gl.start
                gl.start = (round(xNew), round(yNew), round(zNew))   # update start coordinate


                # Update distance from start
                dx, dy, dz = xOrig-xNew, yOrig-yNew, zOrig-zNew
                dfs = sqrt(dx**2 + dy**2 + dz**2)


                # Plot movement and save figure
                if makeMovie:
                    fname = ('_tmp%05d.'+gl.imgformat) %gl.stepCount
                    plt.savefig(fname,dpi=gl.dpi,bbox_inches='tight')
                    frames.append(fname)
                if gl.makeFigure:
                    gl.ax1.plot([xOld,xNew], [yOld,yNew], [zOld,zNew], linewidth=2, c='#5DA5DA')

                # Update total cost of path
                total_cost += L[0].computeCost((xOld, yOld, zOld), (xNew, yNew, zNew), False)


                # Generate random obstacles
                if makeRandObs:
                    fcn.genRandObs(minObs,maxObs,maxPercent,seedDyn)

                # Moving goal execution
                if useMovingGoals:
                    for i in xrange(0,len(initX)):  goalMoved = fcn.movingGoal(initX[i], initY[i], initZ[i], T[i])

                # Update counter used for the two preceding functions
                gl.stepCount += 1

                # Check if there's any obstacles within search radius if we've moved to a different node
                if oldstart != gl.start and not fcn.searchAndUpdate(xNew, yNew, zNew, path):
                    validPath=False
                    break

                # Check if next movement takes us outside of refinement region
                if dfs+1 >= refinementDistance/2 or len(path)<1:
                    validPath = False
                    break

                # if isinf(gl.costMatrix[path[0]]):
                #     validPath = False





    #k = np.nonzero(gl.goals[:,0]==gl.goal[0] and gl.goals[:,1]==gl.goal[1] and gl.goals[:,2]==gl.goal[2]) # find current goal
  #  k = np.where((gl.goals[:,0]==gl.goal[0]) and (gl.goals[:,1]==gl.goal[1]))


    if len(gl.goals) > 1:
        print 'finding next goal...'

        # Identify rows in goals array matching current goal
        k1 = np.where(gl.goals[:,0]==gl.goal[0])
        k2 = np.where(gl.goals[:,1]==gl.goal[1])
        k3 = np.where(gl.goals[:,2]==gl.goal[2])

        # Whichever row shows up in k1, k2, and k3 is the row with the current goal
        k = np.intersect1d(np.intersect1d(k1,k2),k3)


        gl.goalsVisited.append(gl.goals[k,3])           # save its goal ID
        gl.goals = np.delete(gl.goals, k, 0)            # delete that row

        # Find next closest goal with respect to straight line distance
        hyp = {}
        for idx, row in enumerate(gl.goals):
            gx, gy, gz = row[0], row[1], row[2]
            xdist, ydist, zdist = gx-gl.start[0], gy-gl.start[1], gz-gl.start[2]
            hyp[idx] = sqrt(xdist**2 + ydist**2 + zdist**2)

        idx, __ = min(hyp.items(), key=lambda x:x[1])
        gl.goal = (gl.goals[idx,0], gl.goals[idx,1], gl.goals[idx,2])

        # Reconfigure levels (needed to add in successors for new goal node)
        #L = fcn.setupLevels()




# Get averages, in milliseconds
mean_time_findPath = 1000*sum(time_findPath) / len(time_findPath)


# print len(gl.costMatrix)
# print 'Total size: ' + str(fcn.getsizeof(gl.costMatrix))
# print str(fcn.total_size(gl.costMatrix, verbose=False))


def hdstar_outputs():
    return total_cost, gl.closed_list, mean_time_findPath, initialFindPathTime*1000

if not gl.testingMode:
    print 'Run succeeded!\n'
    print 'Elapsed time: ' + str(time.time() - tic) + ' seconds'
    print mean_time_findPath
    print gl.closed_list
    print total_cost


if makeMovie:
    # Save a few extra still frame so video doesn't end abruptly
    print 'Making video....'
    for i in xrange(1,11):
        idx = gl.stepCount+i
        fname = ('_tmp%05d.'+gl.imgformat) %idx
        plt.savefig(fname,dpi=gl.dpi,bbox_inches='tight')
        frames.append(fname)

    # Then make movie
    command = ('mencoder','mf://_tmp*.'+gl.imgformat,'-mf',
           'type='+gl.imgformat+':w=800:h=600:fps='+str(gl.fps),'-ovc',
            'lavc','-lavcopts','vcodec=mpeg4','-oac','copy','-o',gl.vidname+'.avi')
    subprocess.check_call(command)
    for fname in frames: os.remove(fname) # remove temporary images

    print 'Video complete!'

if makeFigure:
    plt.savefig('dstarFig.pdf',bbox_inches='tight')
    print 'Figure is open. Close figure to end script'
    plt.show()

