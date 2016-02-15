from functools import partial

import pytest
from zeno.test.eventually import eventually
from zeno.test.malicious_behaviors_node import makeNodeFaulty, \
    send3PhaseMsgWithIncorrectDigest
from zeno.test.testing_utils import adict

from zeno.common.request_types import Prepare
from zeno.server.suspicion_codes import Suspicions
from zeno.test.helper import getPrimaryReplica, getNonPrimaryReplicas, \
    getNodeSuspicions

whitelist = [Suspicions.PR_DIGEST_WRONG.reason,
             'Invalid prepare message received',
             'cannot process incoming PREPARE',
             Suspicions.CM_DIGEST_WRONG.reason,
             'cannot process incoming COMMIT']


@pytest.fixture("module")
def setup(nodeSet, up):
    primaryRep, nonPrimaryReps = getPrimaryReplica(nodeSet, 0), \
                                 getNonPrimaryReplicas(nodeSet, 0)

    # A non primary replica sends PREPARE messages with incorrect digest

    faultyRep = nonPrimaryReps[0]
    makeNodeFaulty(faultyRep.node, partial(send3PhaseMsgWithIncorrectDigest,
                                           msgType=Prepare, instId=0))

    return adict(primaryRep=primaryRep, nonPrimaryReps=nonPrimaryReps,
                 faultyRep=faultyRep)


# noinspection PyIncorrectDocstring
def testPrepareDigest(setup, looper, sent1):
    """
    A non primary replica sends PREPARE message with incorrect digest to all
    other replicas. Other replicas should raise suspicion the
    PREPARE seen
    """

    primaryRep, nonPrimaryReps, faultyRep = setup.primaryRep, \
                                            setup.nonPrimaryReps, setup.faultyRep

    def chkSusp():
        for r in (primaryRep, *nonPrimaryReps):
            if r.name != faultyRep.name:
                # Every node except the one from which PREPARE with incorrect
                # digest was sent should raise suspicion for the PREPARE
                # message
                assert len(getNodeSuspicions(r.node,
                                             Suspicions.PR_DIGEST_WRONG.code)) == 1

    looper.run(eventually(chkSusp, retryWait=1, timeout=20))