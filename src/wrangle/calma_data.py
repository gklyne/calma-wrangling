"""
CALMA data access functions
"""

from __future__ import print_function

import sys
import os
import re
import json
import urlparse

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import RDF, RDFS  #, DC, FOAF

from miscutils.HttpSessionRDF import HTTP_Session

from wrangle_errors import wrangle_errors, wrangle_unexpected, wrangle_missingarg, wrangle_report

PROV = Namespace("http://www.w3.org/ns/prov#")

def read_rdf(url, graph=None):
    """
    Read analysis from supplied URL
    """
    with HTTP_Session(url) as http:
        (status, reason, headers, rdf) = http.doRequestRDF(url, graph=graph)
        if status != 200:
            return wrangle_report(
                wrangle_errors.HTTPFAIL,
                "HTTP error response %03d %s"%(status, reason)
                )
    return (wrangle_errors.SUCCESS, rdf)

def explore_analysis(srcroot, userhome, userconfig, options):
    """
    Read CALMA analysis data at URI supplied on command line
    and display outline information.
    """
    # Check arguments and read data
    if len(options.args) > 1:
        return wrangle_unexpected(options)
    if len(options.args) == 0:
        return wrangle_missingarg("analysis URL", options)
    url    = options.args[0]
    print("CALMA analysis URL %s"%url)
    status, rdf = read_rdf(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # Poke around data and show some information
    print("Read RDF at %s"%url)
    for t in sorted(set(rdf.objects(None, RDF.type))):
        print("RDF type: %s"%t)
        tt = set()
        for s in rdf.subjects(RDF.type, t):
            tt = tt | set(rdf.objects(s, RDF.type))
        tt.discard(t)
        if tt != set():
            print("    Additional types %s"%([str(ttt) for ttt in sorted(tt)]))
        for s in rdf.subjects(RDF.type, t):
            for p in sorted(set(rdf.predicates(s, None))):
                if p != RDF.type:
                    print("    property: %s"%p)
    # for p in sorted(set(rdf.predicates(None, None))):
    #     print("RDF property: %s"%p)
    return status

def property_name_field_key(rdf, p):
    """
    Return JSON property key for supplied RDF predicate
    """
    prefix, namespace, name = rdf.namespace_manager.compute_qname(p)
    pf = "%s_field"%name
    pk = "%s:%s"%(prefix, name) if prefix else str(p)
    return (name, pf, pk)

def get_type_info(rdf, t):
    """
    Extract basic information about a type: id, prefix, etc.

    Returns a partial type entity structure like this:
    
        { "annal:uri":        "dmo:zzzz"
        , "annal:id":         "zzzz"
        , "rdfs:label":       "..."
        , "rdfs:comment":     "..."
        , "annal:type_list":  "zzzz_list"
        , "annal:type_view":  "zzzz_view"
        }
    """
    prefix, namespace, name = rdf.namespace_manager.compute_qname(t)
    label   = rdf.value(subject=t, predicate=RDFS.label)   or "Type %s:%s"%(prefix, name)
    comment = rdf.value(subject=t, predicate=RDFS.comment) or "Type %s:%s (%s)"%(prefix, name, t)
    td = (
        { "annal:uri":        "%s:%s"%(prefix, name) if prefix else str(t)
        , "annal:id":         name
        , "rdfs:label":       label
        , "rdfs:comment":     comment
        , "annal:type_list":  "%s_list"%name
        , "annal:type_view":  "%s_view"%name
        })
    return td

def get_subject_info(rdf, s):
    """
    Extract information about a generic subject resource
    """
    if not isinstance(s, URIRef): return None
    prefix, namespace, name = rdf.namespace_manager.compute_qname(s)
    label   = rdf.value(subject=s, predicate=RDFS.label)   or "Resource %s:%s"%(prefix, name)
    comment = rdf.value(subject=s, predicate=RDFS.comment) or "Resource %s:%s (%s)"%(prefix, name, s)
    sd = (
        { "annal:uri":        "%s:%s"%(prefix, name) if prefix else str(s)
        , "annal:id":         name
        , "rdfs:label":       label
        , "rdfs:comment":     comment
        , "rdfs:seeAlso":     str(s)
        })
    for p, o in rdf.predicate_objects(s):
        if p != RDF.type:
            pn, pf, pk = property_name_field_key(rdf, p)
            sd[pk] = str(o)
    return sd

def get_activity_info(rdf, s):
    """
    Extract information about an activity resource

    This differs from get_subject_info in that it folds the last part of the URI path
    into the generated entity identifier.
    """
    if not isinstance(s, URIRef): return None
    prefix, namespace, frag = rdf.namespace_manager.compute_qname(s)
    upath = urlparse.urlparse(str(namespace)).path
    uname = upath.rsplit("/",1)[1]
    m = re.search("-([a-z0-9]{12})$", uname)
    if m:
        ustem = m.group(1)
    else:
        ustem = uname.replace("-", "_")
    actid = "%s_%s"%(ustem, frag.replace("-", "_"))
    if len(actid) > 32:
        actid = actid[0:8]+"___"+actid[-20:]
    label   = (
        rdf.value(subject=s, predicate=RDFS.label) or 
        "Resource %s:%s"%(prefix, frag)
        )
    comment = (
        rdf.value(subject=s, predicate=RDFS.comment) or 
        "Resource %s:%s (%s), id %s"%(prefix, frag, s, actid)
        )
    sd = (
        { "annal:uri":        "%s:%s"%(prefix, frag) if prefix else str(s)
        , "annal:id":         actid
        , "rdfs:label":       label
        , "rdfs:comment":     comment
        , "rdfs:seeAlso":     str(s)
        })
    for p, o in rdf.predicate_objects(s):
        if p != RDF.type:
            pn, pf, pk = property_name_field_key(rdf, p)
            sd[pk] = str(o)
    return sd

def export_entity(ef, ed):
    """
    Write entity data to file, creating directories as needed
    """
    try:
        os.makedirs(os.path.dirname(ef))
    except OSError as e:
        # print("Caught OSError: %s"%str(e), file=sys.stderr)
        pass
    with open(ef, "wt") as fs:
        fs.write(json.dumps(ed, indent=2))
    return

def export_type(rdf, t, td, colldir):
    """
    Export Annalist type description for type `t`
    """
    ed = td.copy()
    ed.update(
        { "@id":              "./"
        , "@type":            ["annal:Type"]
        , "annal:type":       "annal:Type"
        , "annal:type_id":    "_type"
        })
    ef = os.path.join(colldir, "_annalist_collection/types/%s/type_meta.jsonld"%td['annal:id'])
    export_entity(ef, ed)
    return

def export_list(rdf, t, td, colldir):
    """
    Export Annalist list description for type `t`
    """
    typename = td['annal:id']
    typeuri  = td['annal:uri']
    listname = td["annal:type_list"]
    viewname = td["annal:type_view"]
    ed = (
        { "@id":                        "./"
        , "@type":                      ["annal:List"]
        , "annal:type":                 "annal:List"
        , "annal:type_id":              "_list"
        , "annal:id":                   listname
        , "rdfs:label":                 "List %s"%typename
        , "rdfs:comment":               "List of %s entities"%typename
        , "annal:display_type":         "List"
        , "annal:default_view":         viewname
        , "annal:default_type":         typename
        , "annal:list_entity_selector": "'%s' in [@type]"%(typeuri)
        , "annal:list_fields":
          [ { "annal:field_id":             "Entity_id"
            , "annal:field_placement":      "small:0,3"
            }
          , { "annal:field_id":             "Entity_label"
            , "annal:field_placement":      "small:3,9"
            }
          ]
        })
    ef = os.path.join(colldir, "_annalist_collection/lists/%s/list_meta.jsonld"%listname)
    export_entity(ef, ed)
    return

def export_view(rdf, t, td, colldir):
    """
    Export Annalist list description for type `t`
    """
    typename = td['annal:id']
    viewname = td["annal:type_view"]
    vd = (
        { "@id":                        "./"
        , "@type":                      ["annal:View"]
        , "annal:type":                 "annal:View"
        , "annal:type_id":              "_list"
        , "annal:id":                   viewname
        , "rdfs:label":                 "View %s"%typename
        , "rdfs:comment":               "View of %s entity"%typename
        , "annal:open_view":            True
        , "annal:view_fields":
          [ { "annal:field_id":         "Entity_id"
            , "annal:field_placement":  "small:0,12;medium:0,6"
            }
          , { "annal:field_id":         "RDF_type"
            , "annal:field_placement":  "small:0,12;medium:0,6"
            }
          , { "annal:field_id":         "RDF_link"
            , "annal:field_placement":  "small:0,12"
            }
          , { "annal:field_id":         "Entity_label"
            , "annal:field_placement":  "small:0,12"
            }
          , { "annal:field_id":         "Entity_comment"
            , "annal:field_placement":  "small:0,12"
            }
          ]
        })
    fields_to_export = set()
    for s in rdf.subjects(RDF.type, t):
        for p in sorted(set(rdf.predicates(s, None))):
            if p != RDF.type:
                pn, pf, pk = property_name_field_key(rdf, p)
                if (pn, pf, pk) not in fields_to_export:
                    # Not already seen for this view: add new field to view
                    vd["annal:view_fields"].append(
                        { "annal:field_id":             pf
                        , "annal:field_placement":      "small:0,12"
                        })
                    fields_to_export.add((pn, pf, pk))
    vf = os.path.join(colldir, "_annalist_collection/views/%s/view_meta.jsonld"%viewname)
    export_entity(vf, vd)
    for pn, pf, pk in fields_to_export:
        export_field(rdf, p, pn, pf, pk, colldir)
    export_field(rdf, RDF.type, "RDF type", "RDF_type", "rdf:type", colldir)
    export_field(rdf, RDF.type, "RDF type", "RDF_type", "annal:type", colldir)
    export_field(rdf, RDFS.seeAlso, "See", "RDF_link", "rdfs:seeAlso", colldir, render="URILink")
    return

def export_field(rdf, p, pn, pf, pk, colldir, render="Text"):
    """
    Export field description for given property name, field id and property key
    """
    fd = (
        { "@id":                        "./"
        , "@type":                      ["annal:Field"]
        , "annal:type":                 "annal:Field"
        , "annal:type_id":              "_field"
        , "annal:id":                   pf
        , "rdfs:label":                 pn
        , "rdfs:comment":               "Field %s (%s, %s)"%(pf, pk, p)
        , "annal:field_render_type":    render
        , "annal:field_value_type":     "annal:Text"
        , "annal:placeholder":          "(%s)"%pf
        , "annal:property_uri":         pk
        , "annal:field_placement":      "small:0,12"
        , "annal:default_value":        ""
        })
    ff = os.path.join(colldir, "_annalist_collection/fields/%s/field_meta.jsonld"%pf)
    export_entity(ff, fd)
    return

def export_subject(rdf, t, td, s, sd, colldir):
    typename = td['annal:id']
    typeuri  = td['annal:uri']
    subjname = sd['annal:id']
    sf = os.path.join(colldir, "d/%s/%s/entity-data.jsonld"%(typename, subjname))
    ed = sd.copy()
    ed.update(
        { "@id":              "./"
        , "@type":            [typeuri]
        , "annal:type":       typeuri
        , "annal:type_id":    typename
        })
    export_entity(sf, ed)
    return

def export_annalist_metadata_from_graph(rdf, colldir):
    for t in sorted(set(rdf.objects(None, RDF.type))):
        if not str(t).startswith(str(RDF)):
            print("Type: %s, export metadata"%t)
            td = get_type_info(rdf, t)
            export_type(rdf, t, td, colldir)
            export_list(rdf, t, td, colldir)
            export_view(rdf, t, td, colldir)
    return wrangle_errors.SUCCESS

def export_annalist_subjects_from_graph(rdf, colldir, get_subject_info=get_subject_info):
    for t in sorted(set(rdf.objects(None, RDF.type))):
        if not str(t).startswith(str(RDF)):
            print("Type: %s, export subjects"%t)
            td = get_type_info(rdf, t)
            for s in rdf.subjects(RDF.type, t):
                print("  Subject %s"%(s))
                sd = get_subject_info(rdf, s)
                if sd:
                    print("  Subject %s/%s"%(td['annal:id'], sd['annal:id']))
                    export_subject(rdf, t, td, s, sd, colldir)
    return wrangle_errors.SUCCESS

def export_annalist_metadata(srcroot, userhome, userconfig, options):
    """
    Read CALMA analysis data at URI supplied on command line
    and export type, list and view definitions
    """
    # Check arguments and read data
    if len(options.args) > 1:
        return wrangle_unexpected(options)
    if len(options.args) == 0:
        return wrangle_missingarg("analysis URL", options)
    url    = options.args[0]
    print("CALMA analysis URL %s"%url)
    status, rdf = read_rdf(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # Poke around data and show some information
    colldir = os.path.join(os.path.expanduser("~"), "annalist_site/c/CALMA_data")
    status  = export_annalist_metadata_from_graph(rdf, colldir)
    return status

def export_annalist_subjects(srcroot, userhome, userconfig, options):
    """
    Read CALMA analysis data at URI supplied on command line
    and export subject data to annalist collection
    """
    # Check arguments and read data
    if len(options.args) > 1:
        return wrangle_unexpected(options)
    if len(options.args) == 0:
        return wrangle_missingarg("analysis URL", options)
    url    = options.args[0]
    print("CALMA analysis URL %s"%url)
    status, rdf = read_rdf(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # Poke around data and show some information
    colldir = os.path.join(os.path.expanduser("~"), "annalist_site/c/CALMA_data")
    status  = export_annalist_subjects_from_graph(rdf, colldir)
    return status

def export_analysis(srcroot, userhome, userconfig, options):
    """
    Read CALMA analysis data at URI supplied on command line
    and export type, list, view and instance data definitions
    """
    # Check arguments and read data
    if len(options.args) > 1:
        return wrangle_unexpected(options)
    if len(options.args) == 0:
        return wrangle_missingarg("analysis URL", options)
    url    = options.args[0]
    print("CALMA analysis URL %s"%url)
    status, rdf = read_rdf(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # Poke around data and show some information
    colldir = os.path.join(os.path.expanduser("~"), "annalist_site/c/CALMA_data")
    status  = export_annalist_metadata_from_graph(rdf, colldir)
    if status != wrangle_errors.SUCCESS:
        return status
    status  = export_annalist_subjects_from_graph(rdf, colldir)
    if status != wrangle_errors.SUCCESS:
        return status
    return status

def export_analyses_multiple(srcroot, userhome, userconfig, options):
    """
    Read analyses listing metadata at given URL and export data for all analyses
    """
    # Check arguments and read analyses listing
    if len(options.args) > 1:
        return wrangle_unexpected(options)
    if len(options.args) == 0:
        return wrangle_missingarg("analyses URL", options)
    url    = options.args[0]
    print("CALMA analyses URL %s"%url)
    status, rdf = read_rdf(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # print("  len(rdf) = %d"%len(rdf))
    # Read referenced analyses and import data to graph
    for a in rdf.subjects(RDF.type, PROV.Activity):
        aurl = str(a)
        print("CALMA analysis URL %s"%aurl)
        status, rdf = read_rdf(aurl, graph=rdf)
        if status != wrangle_errors.SUCCESS:
            return status
        # print("  len(rdf) = %d"%len(rdf))
    # Generate metadata and subject data
    colldir = os.path.join(os.path.expanduser("~"), "annalist_site/c/CALMA_data")
    status  = export_annalist_metadata_from_graph(rdf, colldir)
    if status != wrangle_errors.SUCCESS:
        return status
    status  = export_annalist_subjects_from_graph(
        rdf, colldir, 
        get_subject_info=get_activity_info
        )
    if status != wrangle_errors.SUCCESS:
        return status
    return status

# End.
