from __future__ import division
import time
import os
import subprocess
import math
import numpy as np
import matplotlib.pyplot as plt
import config_program
import all_functions as fcn
import config_user as gl


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

searchRadius, useMovingGoals, smoothPath = gl.searchRadius, gl.useMovingGoals, gl.smoothPath
makeRandObs, makeFigure, makeMovie, numlevels = gl.makeRandObs, gl.makeFigure, gl.makeMovie, gl.numlevels

minObs, maxObs, maxPercent, seedDyn, seedStatic = gl.minObs, gl.maxObs, gl.maxPercent, gl.seedDyn, gl.seedStatic
initX, initY, initZ, T, rXdim, rYdim, rZdim = gl.initX, gl.initY, gl.initZ, gl.T, gl.rXdim, gl.rYdim, gl.rZdim
rXstart, rYstart, rZstart = gl.rXstart, gl.rYstart, gl.rZstart

tic = time.time()
if makeMovie:   frames = []



""" Setup abstract levels """
L = fcn.setupLevels()

#numlevels = 0
""" Begin main algorithm """
for idx in xrange(0, gl.numGoals):                      # for each goal
    xNew, yNew, zNew = fcn.general_n2c(gl.start)        # get current location
    fcn.searchAndUpdate(xNew,yNew,zNew)                 # search for obstacles
    while gl.start != gl.goal:
        oldstart, oldgoal = gl.start, gl.goal         # Line 48 of Moving Target D*Lite

        # 1. Compute coarsest feasible hierarchical path
                # for moving goal: when it moves, check cluster. if new cluster, modify successors
                # for clusters, try only using one "entrance" in the center of each cluster
        nextpos = fcn.findCoarsePath(L)

        #gl.ax1.scatter(gl.startX, gl.startY, gl.startZ, c='y', s=20)
        # for node in new_waypts:
        #     x,y,z = fcn.general_n2c(node)
        #     gl.ax1.scatter(x,y,z, c='b', s=5)

        # 2. Smooth out the lowest level path, which becomes the general path we follow to the goal
        nextpos = fcn.postSmoothPath(nextpos)
        nextpos = [node for node in nextpos if not math.isinf(gl.costMatrix[node])]
        # for node in nextpos:
        #     x,y,z = fcn.general_n2c(node)
        #     gl.ax1.scatter(x,y,z, c='y', s=5)


        validCoarsePath = True
        while validCoarsePath and gl.start != gl.goal:


            # 3. Identify waypoints along this path, a distance apart equal to smallest cluster dimension
            new_waypts = fcn.fromCoarseToWaypoints(nextpos, L)                    # coordinates
            # Getting node numbers for use search and update function
            new_waypts_nodes = [fcn.general_c2n(round(pt[0]), round(pt[1]), round(pt[2])) for pt in new_waypts]


            # for idx,node in enumerate(new_waypoints[0:-1]):
            #     #x1,y1,z1 = fcn.general_n2c(new_waypoints[idx])
            #     #x2,y2,z2 = fcn.general_n2c(node)
            #     x1,y1,z1 = new_waypoints[idx]
            #     x2,y2,z2 = new_waypoints[idx+1]
            #     gl.ax1.plot([x1, x2], [y1, y2], [z1, z2], linewidth=2, c='y')

            # for node in new_waypts:
            #     x,y,z = node
            #     gl.ax1.scatter(x,y,z, c='c', s=5, alpha=0.3)

            hdl = []
            # 4. Compute the shortest level 0 path to each waypoint
            for waypoint in new_waypts:
                wpX,wpY,wpZ = waypoint
                goalnode = fcn.general_c2n(round(wpX),round(wpY),round(wpZ))
                pathToFollow = L[0].computeShortestPathWithWaypoints_L0([gl.start, goalnode])   # get path
                #gl.ax1.scatter(gl.startX, gl.startY, gl.startZ, c='m', s=5)

                # 5. Smooth the path and get the coordinates to move to
                pathToFollow = fcn.postSmoothPath(pathToFollow)
                nextcoords = fcn.fromNodesToCoordinates(pathToFollow)
                nextcoords_nodes = [fcn.general_c2n(round(pt[0]), round(pt[1]), round(pt[2])) for pt in nextcoords]
                # Line 53 of Moving Target D* Lite is computed within below while loop
                # Line 54 of Moving Target D* Lite begins here
                goalMoved, validCoarsePath, validL0Path = False, True, True

                while not goalMoved and validCoarsePath and validL0Path:
                    # Save current position
                    xOld, yOld, zOld = xNew, yNew, zNew

                    # Move to the next point
                    xNew, yNew, zNew = nextcoords[-1,0], nextcoords[-1,1], nextcoords[-1,2]
                    nextcoords = np.delete(nextcoords, -1, 0)

                    # Update start coordinate
                    gl.start = fcn.general_c2n(round(xNew), round(yNew), round(zNew))
                    gl.startX, gl.startY, gl.startZ = xNew, yNew, zNew

                    # Plot movement and save figure
                    if makeMovie:
                        fname = ('_tmp%05d.'+gl.imgformat) %gl.stepCount
                        plt.savefig(fname,dpi=gl.dpi,bbox_inches='tight')
                        frames.append(fname)
                    gl.ax1.plot([xOld,xNew], [yOld,yNew], [zOld,zNew], linewidth=2, c='#5DA5DA')

                    # Generate random obstacles
                    if makeRandObs:     fcn.genRandObs(minObs,maxObs,maxPercent,seedDyn)

                    # Moving goal execution
                    if useMovingGoals:
                        for i in xrange(0,len(initX)):  goalMoved = fcn.movingGoal(initX[i], initY[i], initZ[i], T[i])

                    gl.stepCount += 1

                    # Search time
                    validCoarsePath, validL0Path = fcn.searchAndUpdate(xNew, yNew, zNew, new_waypts_nodes, nextcoords_nodes)

                    # If we reached the intermediate waypoint, move to next waypoint
                    if xNew == round(wpX) and yNew == round(wpY) and zNew == round(wpZ):
                        goalMoved = True
                        break

                    # # Recalculate coarse path if it becomes invalid
                    # if goalMoved or newObsExist:
                    #     break
                    #
                    if not validCoarsePath:
                        break

                if not validCoarsePath:
                    break





    k = np.nonzero(gl.goals[:,3]==gl.goal)[0][0]                    # find current goal
    gl.goalsVisited.append(gl.goals[k,4])                           # save its goal ID
    gl.goals = np.delete(gl.goals, k, 0)                            # remove that row
    gl.startX,gl.startY,gl.startZ = fcn.general_n2c(gl.start)       # get start coordinates

    if len(gl.goals) > 0:
        print 'finding next goal...'

        # Find next closest goal w.r.t. straight line distance
        hyp = {}
        for i in gl.goals:
            gx, gy, gz, gs = i[0], i[1], i[2], i[3]
            xdist, ydist, zdist = gx-gl.startX, gy-gl.startY, gz-gl.startZ
            hyp[gs] = math.sqrt(xdist**2 + ydist**2 + zdist**2)

        gl.goal, __ = min(hyp.items(), key=lambda x:x[1])

        gl.goalX, gl.goalY, gl.goalZ = fcn.general_n2c(gl.goal)

        # Reconfigure levels (needed to add in successors for new goal node)
        L = fcn.setupLevels()








print 'Run succeeded!'
print 'Elapsed time: ' + str(time.time() - tic) + ' seconds'

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
    print 'Figure is open. Close figure to end script'
    plt.savefig('dstarFig.pdf',bbox_inches='tight')
    plt.show()





