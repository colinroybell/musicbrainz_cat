import musicbrainzngs
import json
import os.path
import time
import sys
import re
import copy

# This sorts out unicode for debugging for now
sys.stdout = open(1, 'w', encoding='utf-8', closefd=False);


type_lookup = {
    'A':'artist',
    'E':'event',
    'G':'release-group',
    'I':'instrument',
    'L':'label',
    'P':'place',
    'R':'release',
    'S':'series',
    'T':'recording',
    'U':'url',
    'W':'work',
    'Z':'area'}

data = {}
for _, object_type in type_lookup.items():
    data[object_type] = {}

if os.path.exists('cache/mb.json'):
    with open('cache/mb.json','r') as f:
        mb_cache = json.load(f)

else:
    mb_cache = {}
    for _, object_type in type_lookup.items():
        mb_cache[object_type] = {}


catalogue = {}
catalogue['class-composers'] = {}
catalogue['class-recitals'] = {}
catalogue['nonclass-artists'] = {}
catalogue['nonclass-compilations'] = {}

musicbrainzngs.set_rate_limit(limit_or_interval=1,new_requests=1)
musicbrainzngs.set_useragent("crb_tagger","0.1",contact="colin@ps116.org.uk")

def musicbrainz_request(type_id):
    print("Requesting type_id {}".format(type_id),flush=True)
    id = type_id[2:]


    object_type = type_lookup[type_id[0]]

    if id in mb_cache[object_type]:
        print("In cache")
        data[object_type][id]=copy.deepcopy(mb_cache[object_type][id])
        return data[object_type][id]

    print(type_id)


    time.sleep(0.1)

    try:
        if object_type == 'release-group':
            result = musicbrainzngs.get_release_group_by_id(id, includes=['releases','release-rels'])
        elif object_type == 'release':
            result =  musicbrainzngs.get_release_by_id(id, includes=['discids','recordings','artists','instrument-rels'])
        elif object_type == 'recording':
             result =  musicbrainzngs.get_recording_by_id(id, includes=['artists','instrument-rels','work-rels','artist-rels','releases'])
        elif object_type == 'work':
             result =  musicbrainzngs.get_work_by_id(id, includes=['artist-rels','work-rels'])


    except  musicbrainzngs.ResponseError as err:
        if err.cause.code == 404:
            sys.exit("Not found")
            return None
        else:
            sys.exit("received bad response {} from the MB server".format(err.cause.code))
            return None

    mb_cache[object_type][id] = copy.deepcopy(result)
    data[object_type][id] = copy.deepcopy(result)
    return result

def catalogue_recordings():
    for rec_id, rec_dat in data['recording'].items():
        if 'processed' in rec_dat:
            continue

        credit_phrase = rec_dat['recording']['artist-credit-phrase']
        if 'work-relation-list' in rec_dat['recording']:
            work_id = recording_to_work(rec_id)
            while work_id:
                work_dat = musicbrainz_request('W-'+work_id)
                superwork_id = get_superwork(work_id)
                if superwork_id:
                    work_id = superwork_id
                    pass
                else:
                    composer = work_to_composer_name(work_id)
                    work_id = None
                    class_cat = catalogue['class-composers']
                    if composer not in class_cat:
                        class_cat[composer] = {}
                        print(composer)
                    title = work_dat['work']['title']
                    if title not in class_cat[composer]:
                        class_cat[composer][title] = []
                    if credit_phrase not in class_cat[composer][title]:
                        class_cat[composer][title].append(credit_phrase)

def recording_to_work(rec_id):
    rec_dat = data ['recording'][rec_id]
    work_id = rec_dat['recording']['work-relation-list'][0]['work']['id']
    return work_id

def work_to_composer_name(work_id):
    work_dat = data['work'][work_id]
    composer = "unknown"
    for artist_rel_dat in work_dat['work']['artist-relation-list']:
        if artist_rel_dat['type'] == 'composer':
            composer = artist_rel_dat['artist']['sort-name']
    return composer

def get_superwork(work_id):
    print(work_id)
    superwork = None
    work_dat = data['work'][work_id]
    if 'work-relation-list' in work_dat['work']:
        for wrl_node in work_dat['work']['work-relation-list']:
            if wrl_node['direction'] == 'backward' and wrl_node['type'] == 'parts':
                if 'attribute-list' in wrl_node:
                    if 'part of collection' in wrl_node['attribute-list']:
                        continue
                #assert superwork == None, "superwork duplicate for work id {}".format(work_id)
                superwork = wrl_node['work']['id']
    return superwork

def add_owned(type_id):
    type_char = type_id[0]
    id = type_id[2:]
    if type_char == 'G': # recording group
        rg_dat = musicbrainz_request(type_id)
        data['recording-group'][id]['owned']='CD'
        for release in rg_dat['release-group']['release-list']:
            add_owned('R-'+release['id'])

    elif type_char == 'R': # release
        rel_dat = musicbrainz_request(type_id)
        data['release'][id]['owned']='CD'
        medium_list = rel_dat['release']['medium-list']
        for medium in medium_list:
            print("Processing disc {}".format(medium['position']))
            for track in medium['track-list']:
                rec_id = track['recording']['id']
                add_owned('T-'+rec_id)
    elif type_char == 'T': # recording
        rec_dat = musicbrainz_request(type_id)
        data['recording'][id]['owned']='CD'

comment_regex = re.compile(r'\s*\#.*')

with open('data/mbcat.in.txt','r') as f:
    for line in f:
        line = line.strip()
        line = comment_regex.sub('',line)
        if line:
            add_owned(line)

catalogue_recordings()

class_cat = catalogue['class-composers']
for composer, _ in sorted(class_cat.items()):
    print("{}".format(composer))
    for work, artists in sorted(class_cat[composer].items()):
        print("    {}".format(work))
        for artist in sorted(artists):
            print("        {}".format(artist))
    print("")

with open('cache/mb.json','w') as f:
    json.dump(mb_cache,f)
