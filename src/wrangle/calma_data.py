"""
CALMA data access functions
"""

from __future__ import print_function

import os
import sys
import json

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import RDF, RDFS  #, DC, FOAF

from miscutils.HttpSessionRDF import HTTP_Session

from wrangle_errors import wrangle_errors, wrangle_unexpected, wrangle_missingarg, wrangle_report

def read_analysis(url):
    """
    Read analysis from supplied URL
    """
    with HTTP_Session(url) as http:
        (status, reason, headers, rdf) = http.doRequestRDF(url)
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
    status, rdf = read_analysis(url)
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
    Extract information about a subject resource
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
    return

def export_field(rdf, p, pn, pf, pk, colldir):
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
        , "annal:field_render_type":    "Text"
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

def export_analysis(srcroot, userhome, userconfig, options):
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
    status, rdf = read_analysis(url)
    if status != wrangle_errors.SUCCESS:
        return status
    # Poke around data and show some information
    for t in sorted(set(rdf.objects(None, RDF.type))):
        if not str(t).startswith(str(RDF)):
            print("Type: %s"%t)
            td = get_type_info(rdf, t)
            colldir = os.path.join(os.path.expanduser("~"), "annalist_site/c/CALMA_data")
            export_type(rdf, t, td, colldir)
            export_list(rdf, t, td, colldir)
            export_view(rdf, t, td, colldir)
            for s in rdf.subjects(RDF.type, t):
                # print("  Subject %s"%(s))
                sd = get_subject_info(rdf, s)
                if sd:
                    print("  Subject %s/%s"%(td['annal:id'], sd['annal:id']))
                    export_subject(rdf, t, td, s, sd, colldir)
    return status

# End.
