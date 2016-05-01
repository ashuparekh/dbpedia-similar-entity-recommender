import urllib2
import json
import re
from SPARQLWrapper import *
from rdflib import *
from __builtin__ import True
import datetime
import operator
import pprint
from json2html import *
import sys
from alchemyapi import *
import time

similar_resources = []


def get_abstract(results):
    '''
    Returns the abstract from the results
    '''
    for result in results["results"]["bindings"]:
        prop = result["prop"]["value"]
        value = result["value"]["value"]
        if "abstract" in prop and 'en' in result["value"]["xml:lang"]:
            abstract = value
            return abstract


def alchemy_concepts(abstract):
    '''
    Retrieves the list of related concepts using AlchemyAPI
    '''
    alchemyapi = AlchemyAPI()
    demo_text = abstract
    concepts = []
    response = alchemyapi.concepts('text', demo_text)

    if response['status'] == 'OK':
        for concept in response['concepts']:
            concepts.append(
                [concept['dbpedia'], round(float(concept['relevance']), 1)])

    else:
        concepts = None

    return concepts


def get_resource_type(results):
    '''
    Computes the resource type of the resource.
    Example:For resource =' Iron_Maiden', returns resource_type = 'http://dbpedia.org/ontology/Organisation'
    '''
    resource_type = None
    for result in results["results"]["bindings"]:
        prop = result["prop"]["value"]
        value = result["value"]["value"]
        if "#type" in prop:
            if "dbpedia.org/ontology" in value:
                resource_type = value
    if resource_type is None:
        return "http://www.w3.org/2002/07/owl#Thing"
    else:
        return resource_type


def get_distractors(resource, resource_type):

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")

    query1 = """

    select ?similar (count(?p) as ?similarity)  where {
      values ?res {<http://dbpedia.org/resource/""" + resource + """>}
      ?similar ?p ?o ; a <""" + resource_type + """> .
      ?res   ?p ?o .

    }
    group by ?similar ?res
    having (count(?p) > 1)
    order by desc(?similarity)
    LIMIT 30
    """

    sparql.setQuery(query1)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    del similar_resources[:]
    for result in results["results"]["bindings"]:
        res = result["similar"]["value"]
        value = result["similarity"]["value"]
        similar_resources.append([res, int(value), 0, 0])
    #   print res + "  " + value

ans = []


def total_one_degree_paths(res1, res2):
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")

    query1 = """

   select count(distinct ?var3) as ?cnt where
{
{
SELECT distinct ?var3
WHERE {
    <http://dbpedia.org/resource/""" + res1 + """> ?prop1 ?var3 .
<""" + res2 + """> ?pr ?var3.
}
}
UNION
{
SELECT distinct ?var3
WHERE {
    <http://dbpedia.org/resource/""" + res1 + """> ?prop1 ?var3 .

?var3 ?prop <""" + res2 + """> .
}
}
}
    """

    sparql.setQuery(query1)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    for result in results["results"]["bindings"]:
        return result["cnt"]["value"]


def get_similar_resources(resource):

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query1 = """
    select distinct ?prop ?value
    where {
    <http://dbpedia.org/resource/""" + resource + """> ?prop ?value }
      """

    sparql.setQuery(query1)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    resource_type = get_resource_type(results)
    get_distractors(resource, resource_type)
    # Alchemy API Part starts
    abstract = get_abstract(results)
    concepts = alchemy_concepts(abstract)

    for concept in concepts:
        for res in similar_resources:
            if concept[0] == res[0]:
                res[2] = concept[1]

    for res in similar_resources:
        res[3] = int(total_one_degree_paths(resource, res[0]))

    similar_resources.sort(key=lambda x: (-x[2], -x[1], -x[3]))
    # Alchemy API part ends
    tot_val = len(similar_resources)
    tot = '"total": "' + str(tot_val) + '", '
    ans = '{' + tot + '  "error": "0" , "resources": ['
    res = ""
    i = 1
    for x in similar_resources:
        res += """
        {
    "rank": \"""" + str(i) + """\",
    "dbpedia": \"""" + x[0] + """\",
    "similarity": \"""" + str(x[1]) + """\",
    "alchemy": \"""" + str(x[2]) + """\",
    "paths": \"""" + str(x[3]) + """\"
    },"""
        i += 1

    ans += res
    ans = ans[0:-1]
    ans += ']}'
    json_obj = json.loads(ans, strict=False)
    ans = json.dumps(json_obj, indent=4)

    print ans

get_similar_resources("India")