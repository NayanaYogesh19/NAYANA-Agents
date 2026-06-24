from policy_retrieval.policies import POLICIES
from precedent_retrieval.precedents import PRECEDENTS



def get_policy(resolution_type):

    return POLICIES.get(

        resolution_type,

        {

            "policy_name":"General Governance Policy",

            "checks":["Governance Review"]

        }

    )


def get_precedents(resolution_type):

    return PRECEDENTS.get(

        resolution_type,

        []

    )