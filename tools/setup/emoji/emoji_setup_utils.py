from __future__ import absolute_import

from collections import defaultdict
from itertools import permutations, chain
import ujson

from six.moves import range, zip
from typing import Text

# the corresponding code point will be set to exactly these names as a final pass,
# overriding any other rules
whitelisted_names = [
    ['date', 'calendar'], ['shirt', 'tshirt'], ['cupid', 'heart_with_arrow'],
    ['tada', 'party_popper'], ['parking', 'p_button'], ['car', 'automobile'],
    ['mortar_board', 'graduation_cap'], ['cd', 'optical_disc'], ['tv', 'television'],
    ['sound', 'speaker_on'], ['mute', 'speaker_off'], ['antenna_bars', 'signal_strength'],
    ['mag_right', 'right_pointing_magnifying_glass'], ['mag', 'left_pointing_magnifying_glass'],
    ['loud_sound', 'speaker_loud'], ['rice_scene', 'moon_ceremony'],
    ['fast_up_button', 'arrow_double_up'], ['fast_down_button', 'arrow_double_down'],
    ['rewind', 'fast_reverse_button'], ['100', 'hundred_points'], ['muscle', 'flexed_biceps'],
    ['walking', 'pedestrian'], ['email', 'envelope'], ['dart', 'direct_hit'],
    ['wc', 'water_closet'], ['zap', 'high_voltage'], ['underage', 'no_one_under_eighteen'],
    ['vhs', 'videocassette'], ['bangbang', 'double_exclamation_mark'],
    ['gun', 'pistol'], ['hocho', 'kitchen_knife'], ['8ball', 'billiards'],
    ['pray', 'folded_hands'], ['cop', 'police_officer'], ['phone', 'telephone'],
    ['bee', 'honeybee'], ['lips', 'mouth'], ['boat', 'sailboat'], ['feet', 'paw_prints'],
    ['uk', 'gb'], ['alien_monster', 'space_invader'], ['reverse_button', 'arrow_backward'],
    # both github and slack remove play_button, though I think this is better
    ['play_button', 'arrow_forward'],
    # github/slack both get rid of shuffle_tracks_button, which seems wrong
    ['shuffle_tracks_button', 'twisted_rightwards_arrows'],
    ['iphone', 'mobile_phone'], # disagrees with github/slack/emojione
    # both github and slack remove {growing,beating}_heart, not sure what I think
    ['heartpulse', 'growing_heart'], ['heartbeat', 'beating_heart'],
    # did remove cityscape_at_dusk from (city_sunset, cityscape_at_dusk)
    ['sunset', 'city_sunrise'],
    ['punch', 'oncoming_fist'], # doesn't include facepunch
    ['+1', 'thumbs_up'], # doesn't include thumbsup
    ['-1', 'thumbs_down'], # doesn't include thumbsdown
    # shit, hankey. slack allows poop, shit, hankey. github calls it hankey,
    # and autocompletes for poop and shit. emojione calls it poop, and
    # autocompletes for pile_of_poo and shit.
    ['poop', 'pile_of_poo'],
    # github/slack remove cooking, but their emoji for this is an uncooked egg
    ['egg', 'cooking'],
    # ['ocean', 'water_wave'], wave is so common that we want it to point only to :wave:
]

blacklisted_names = frozenset([
    # would be chosen by words_supersets or superstrings
    'football', # american_football
    'post_office', # european_post_office (there's also a japanese_post_office)
    'castle', # european_castle (there's also a japanese_castle)
    'chart', # chart_increasing_with_yen (should rename chart_increasing to chart)
    'loop', # double_curly_loop (should rename curly_loop to loop)
    'massage', # face_massage
    'bulb', # light_bulb
    'barber', # barber_pole
    'mens', # mens_room
    'womens', # womens_room
    'knife', # kitchen_knife (hocho also maps here)
    'notes', # musical_notes
    'beetle', # lady_beetle
    'ab', # ab_button (due to keeping a_button, due to the one_lettered() rule)
    'headphone', # headphones
    'mega', # megaphone
    'ski', # skis
    'high_heel', # high_heeled_shoe (so that it shows up when searching for shoe)
    # less confident about the following
    'dolls', # japanese_dolls
    'moon', # waxing_gibbous_moon (should rename crescent_moon to moon)
    'clapper', # clapper_board
    'traffic_light', # horizontal_traffic_light (there's also a vertical_traffic_light)
    'lantern',
    'red_paper_lantern', # izakaya_lantern (in the future we should make sure
                         # red_paper_lantern finds this)

    # would be chosen by longer
    'down_button', # arrow_down_small, I think to match the other arrow_*
                   # names. Matching what github and slack do.
    'running_shoe', # athletic_shoe, both github and slack agree here.
    'running', # runner. slack has both, github has running_man and running_woman, but not runner
    'o2', # o_button
    'star2', # glowing_star
    'bright', # high_brightness, to match low_brightness, what github/slack do
    'dim_button', # low_brightness, copying github/slack
    'stars', # shooting_star. disagrees with github, slack, and emojione, but this seems better
    'nail_care', # nail_polish. Also disagrees github/slack/emojione, is nail_polish mostly an
                 # american thing?
    'busstop', # bus_stop
    'tophat', # top_hat
    'old_woman', # older_woman, following github/slack/emojione on these
    'old_man', # older_man
    'blue_car', # recreational_vehicle
    'litter_in_bin_sign', # put_litter_in_its_place
    'moai', # moyai based on github/slack
    'fuelpump', # fuel_pump

    # names not otherwise excluded by our heuristics
    'left_arrow', # arrow_left, to match other arrow_* shortnames
    'right_arrow', # arrow_right
    'up_arrow', # arrow_up
    'down_arrow', # arrow_down
    'chequered_flag', # checkered_flag
    'e_mail', # e-mail
    'non_potable_water', # non-potable_water
    'flipper', # dolphin
])

## functions that take in a list of names at a codepoint and return a subset to exclude

def blacklisted(names):
    # type: (List[str]) -> List[str]
    return [name for name in names if name in blacklisted_names]

# 1 letter names don't currently show up in our autocomplete. Maybe should
# change our autocomplete so that a whitelist of letters do, like j (for joy), x, etc
# github uses a, ab, etc. instead of a_button, slack doesn't have any of the [letter]_buttons
def one_lettered(names):
    # type: (List[str]) -> List[str]
    if len(names) == 1:
        return []
    return [name for name in names if len(name) == 1]

# If it is an ideograph (or katakana, but we'll probably deal with that
# differently after 1.5), remove any names that don't have
# ideograph/katakana in them
def ideographless(names):
    # type: (List[str]) -> List[str]
    has_ideographs = ['ideograph' in name.split('_') or
                      'katakana' in name.split('_') for name in names]
    if not any(has_ideographs):
        return []
    return [name for name, has_ideograph in zip(names, has_ideographs) if not has_ideograph]

# subsumed by longer, but still useful for breaking up a hand review of the
# blacklist decisions
def word_superset(names):
    # type: (List[str]) -> List[str]
    bags_of_words = [frozenset(name.split('_')) for name in names]
    bad_names = set()
    for i, j in permutations(list(range(len(names))), 2):
        if bags_of_words[i] < bags_of_words[j]:
            bad_names.add(names[j])
    return list(bad_names)

# subsumed by longer, but still useful for breaking up a hand review of the
# blacklist decisions
def superstring(names):
    # type: (List[str]) -> List[str]
    bad_names = set()
    for name1, name2 in permutations(names, 2):
        if name2[:len(name1)] == name1:
            bad_names.add(name2)
    return list(bad_names)

def longer(names):
    # type: (List[str]) -> List[str]
    lengths = [len(name) for name in names]
    min_length = min(lengths)
    return [name for name, length in zip(names, lengths) if length > min_length]

def emoji_names_for_picker(emoji_map):
    # type: (Dict[Text, Text]) -> List[str]
    codepoint_to_names = defaultdict(list) # type: Dict[Text, List[str]]
    for name, codepoint in emoji_map.items():
        codepoint_to_names[codepoint].append(str(name))

    # blacklisted must come first, followed by {one_lettered, ideographless}
    # Each function here returns a list of names to be removed from a list of names
    for func in [blacklisted, one_lettered, ideographless, word_superset, superstring, longer]:
        for codepoint, names in codepoint_to_names.items():
            codepoint_to_names[codepoint] = [name for name in names if name not in func(names)]

    for names in whitelisted_names:
        codepoint = emoji_map[names[0]]
        for name in names:
            assert (emoji_map[name] == codepoint)
        codepoint_to_names[codepoint] = names

    return sorted(list(chain.from_iterable(codepoint_to_names.values())))
