// Copies the curated vanilla reference icons out of the Godot conversion dump into
// .tools/art/ref/{powers,relics}/<id>.png with clean names, and writes a small JSON index.
//
// Also reports the native size of every source so we can state it in the report.
// Usage: node collect-refs.js
'use strict';
const fs = require('fs');
const path = require('path');

const SRC = 'C:\\temp\\artref\\out';
const DEST = 'D:\\桌面\\sts2mod\\.tools\\art\\ref';

// my subject -> the closest vanilla icon(s), used for the contact sheet + the style sample
const POWER_PAIRS = {
  prophet_tally:      ['countdown_power', 'foregone_conclusion_power'],
  foresight:          ['anticipate_power', 'master_planner_power'],
  nirvana:            ['hardened_shell_power', 'plating_power'],
  prophetic_study:    ['machine_learning_power', 'master_planner_power'],
  cycle_of_prophecy:  ['loop_power', 'iteration_power'],
  pure_love_form:     ['echo_form_power', 'demon_form_power'],
  delayed_echo:       ['duplication_power', 'echo_form_power'],
  delayed_scry:       ['clarity_power', 'anticipate_power'],
  scry_might:         ['strength_power', 'possess_strength_power'],
  scry_agility:       ['dexterity_power', 'possess_speed_power'],
  judgement:          ['doom_power', 'oblivion_power'],
  ember_boon:         ['flame_barrier_power', 'pyre_power'],
  granted_turn:       ['energy_next_turn_power', 'star_next_turn_power'],
  insight:            ['clarity_power', 'foregone_conclusion_power'],
  purify:             ['spirit_of_ash_power', 'feel_no_pain_power'],
  exhaust_blast:      ['spirit_of_ash_power', 'demise_power'],
  free_status:        ['free_power_power', 'free_skill_power'],
  double_status:      ['duplication_power', 'double_damage_power'],
  status_draw:        ['draw_cards_next_turn_power', 'tools_of_the_trade_power'],
  shared_might:       ['leadership_power', 'coordinate_power'],
  steady_agility:     ['plating_power', 'dexterity_power'],
  starscar_form:      ['star_next_turn_power', 'void_form_power'],
  foresight:          ['anticipate_power', 'master_planner_power'],
  nirvana:            ['hardened_shell_power', 'plating_power'],
};

const RELIC_PAIRS = {
  agate_potion_belt:  ['potion_belt', 'belt_buckle'],
  foresight_charm:    ['planisphere', 'arcane_scroll'],
  prophets_bracelet:  ['beautiful_bracelet', 'juzu_bracelet'],
  prophets_eye:       ['paels_eye', 'glass_eye'],
  prophets_eye_plus:  ['paels_eye', 'glass_eye'],
};

// plus a broad, unbiased sample purely for the style statistics
const EXTRA_POWERS = [
  'accuracy_power', 'aggression_power', 'artifact_power', 'barricade_power', 'blur_power',
  'buffer_power', 'corruption_power', 'cruelty_power', 'curl_up_power', 'inferno_power',
  'dark_embrace_power', 'envenom_power', 'fasten_power', 'feral_power', 'flame_barrier_power',
  'focus_power', 'frail_power', 'juggernaut_power', 'loop_power', 'mayhem_power',
  'noxious_fumes_power', 'panache_power', 'poison_power', 'rage_power', 'regen_power',
  'ritual_power', 'shackling_potion_power', 'speed_potion_power', 'storm_power', 'thorns_power',
  'vigor_power', 'vulnerable_power', 'weak_power', 'well_laid_plans_power', 'wraith_form_power',
  'intangible_power', 'hard_to_kill_power', 'echo_form_power', 'radiance_power', 'star_next_turn_power',
];
const EXTRA_RELICS = [
  'akabeko', 'anchor', 'arcane_scroll', 'art_of_war', 'astrolabe', 'bag_of_marbles',
  'bag_of_preparation', 'beating_remnant', 'bellows', 'belt_buckle', 'blood_vial', 'bronze_scales',
  'burning_blood', 'centennial_puzzle', 'chandelier', 'chemical_x', 'crossbow',
  'cracked_core', 'darkstone_periapt', 'dream_catcher', 'diamond_diadem', 'data_disk',
  'ectoplasm', 'empty_cage', 'frozen_egg', 'gambling_chip', 'glass_eye', 'glitter',
  'gorget', 'gremlin_horn', 'happy_flower', 'ice_cream', 'jewelry_box', 'ink_bottle',
  'kunai', 'lantern', 'letter_opener', 'lizard_tail', 'mango', 'meat_on_the_bone',
];

function index() {
  const byId = new Map();
  for (const f of fs.readdirSync(SRC)) {
    if (!f.endsWith('.png')) continue;
    const m = /^(power|relic)__([a-z0-9_]+)__/.exec(f);
    if (!m) continue;
    byId.set(m[1] + '/' + m[2], f);
  }
  return byId;
}

const byId = index();
console.log('vanilla icons available: powers=' +
  [...byId.keys()].filter(k => k.startsWith('power/')).length +
  ' relics=' + [...byId.keys()].filter(k => k.startsWith('relic/')).length);

fs.mkdirSync(path.join(DEST, 'powers'), { recursive: true });
fs.mkdirSync(path.join(DEST, 'relics'), { recursive: true });

const copied = [];
const missing = [];
function copy(kind, id) {
  const key = kind + '/' + id;
  const src = byId.get(key);
  if (!src) { missing.push(key); return null; }
  const dst = path.join(DEST, kind + 's', id + '.png');
  fs.copyFileSync(path.join(SRC, src), dst);
  copied.push({ kind, id, src: src, dst });
  return dst;
}

// 1. every semantic pair target
for (const [, pair] of Object.entries(POWER_PAIRS)) for (const id of pair) copy('power', id);
for (const [, pair] of Object.entries(RELIC_PAIRS)) for (const id of pair) copy('relic', id);
// 2. the broad statistical sample
for (const id of EXTRA_POWERS) copy('power', id);
for (const id of EXTRA_RELICS) copy('relic', id);

const pairs = {};
for (const [mine, list] of Object.entries(POWER_PAIRS)) pairs['power/' + mine] = list.filter(id => byId.has('power/' + id));
for (const [mine, list] of Object.entries(RELIC_PAIRS)) pairs['relic/' + mine] = list.filter(id => byId.has('relic/' + id));

fs.writeFileSync(path.join(DEST, 'pairs.json'), JSON.stringify(pairs, null, 2), 'utf8');
fs.writeFileSync(path.join(DEST, 'copied.json'), JSON.stringify(copied, null, 2), 'utf8');

const nPow = copied.filter(c => c.kind === 'power').length;
const nRel = copied.filter(c => c.kind === 'relic').length;
console.log('copied powers=' + nPow + ' relics=' + nRel + ' -> ' + DEST);
if (missing.length) console.log('MISSING (' + missing.length + '): ' + missing.join(', '));
