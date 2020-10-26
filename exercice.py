#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mido
import json
import csv
import os
import time
import configparser
from copy import deepcopy

import inputs
import mido



NOTES_PER_OCTAVE = 12


def build_note_dictionaries(note_names, add_octave_no=True):
	C0_MIDI_NO = 12 # Plus basse note sur les pianos est La 0, mais on va commencer à générer les noms sur Do 0

	midi_to_name = {}
	name_to_midi = {}
	# Pour chaque octave de 0 à 8 (inclus). On va générer tout l'octave 8, même si la dernière note du piano est Do 8
	for octave in range(8+1):
		# Pour chaque note de l'octave
		for note in range(NOTES_PER_OCTAVE):
			# Calculer le numéro MIDI de la note et ajouter aux deux dictionnaires
			midi_no = C0_MIDI_NO + octave * NOTES_PER_OCTAVE + note
			# Ajouter le numéro de l'octave au nom de la note si add_octave_no est vrai
			full_note_name = note_names[note] + (str(octave) if add_octave_no else "")
			midi_to_name[midi_no] = full_note_name
			# Garder les numéros de notes dans name_to_midi entre 0 et 11 si add_octave_no est faux
			name_to_midi[full_note_name] = midi_no if add_octave_no else midi_no % NOTES_PER_OCTAVE
	return midi_to_name, name_to_midi

def build_note_callbacks(note_name, name_to_midi, midi_outputs):
	def action_fn_pressed():
		msg = mido.Message("note_on", note=name_to_midi[note_name], velocity=80)
		for o in midi_outputs:
			o.send(msg)
	def action_fn_released():
		msg = mido.Message("note_off", note=name_to_midi[note_name])
		for o in midi_outputs:
			o.send(msg)
	return action_fn_pressed, action_fn_released

def build_chord_callbacks(chord, chord_notes, name_to_midi, midi_outputs):
	def action_fn_pressed():
		for note in chord_notes[chord]:
			msg = mido.Message("note_on", note=name_to_midi[note], velocity=80)
			for o in midi_outputs:
				o.send(msg)
	def action_fn_released():
		for note in chord_notes[chord]:
			msg = mido.Message("note_off", note=name_to_midi[note])
			for o in midi_outputs:
				o.send(msg)
	return action_fn_pressed, action_fn_released

def build_custom_action_callbacks(action_name, custom_actions, midi_outputs):
	pressed, released = None, None
	if custom_actions[action_name][True] is not None:
		def action_fn_pressed():
			custom_actions[action_name][True](midi_outputs)
		pressed = action_fn_pressed
	if custom_actions[action_name][False] is not None:
		def action_fn_released():
			custom_actions[action_name][False](midi_outputs)
		released = action_fn_released
	return pressed, released

def load_input_mappings(filename, name_to_midi, chord_notes, midi_outputs, custom_actions={}):
	config = configparser.ConfigParser()
	config.read(filename)
	gamepad_section = config["gamepad"]

	mappings = {}
	for gamepad_input in gamepad_section:
		action_name = gamepad_section[gamepad_input]
		if action_name in name_to_midi:
			pressed, released = build_note_callbacks(action_name, name_to_midi, midi_outputs)
			mappings[gamepad_input] = {True: pressed, False: released}
		elif action_name in chord_notes:
			pressed, released = build_chord_callbacks(action_name, chord_notes, name_to_midi, midi_outputs)
			mappings[gamepad_input] = {True: pressed, False: released}
		elif action_name in custom_actions:
			pressed, released = build_custom_action_callbacks(action_name, custom_actions, midi_outputs)
			mappings[gamepad_input] = {True: pressed, False: released}
	return mappings



def main():
	gamepad = inputs.devices.gamepads[0]
	midi_outputs = (mido.open_output("UM-ONE 3"), mido.open_output("UnPortMIDI 4"))
	midi_input = mido.open_input("UM-ONE 0")

	notes_data = json.load(open("notes.json", "r"))
	note_names = notes_data["solfeggio_names"]
	midi_to_name, name_to_midi = build_note_dictionaries(note_names)
	chords = notes_data["chords"]

	def foo0(midi_outputs):
		print("henlo")
	def foo1(midi_outputs):
		print("k bye")
	custom_actions = {
		"foo": {True: foo0, False: foo1}
	}

	mappings = load_input_mappings("input.ini", name_to_midi, chords, midi_outputs, custom_actions)

	while True:
		for e in gamepad.read():
			#if e.ev_type not in ("Sync") and e.code not in ("ABS_X", "ABS_Y","ABS_RX", "ABS_RY"):
			#	print(e.ev_type, e.code, e.state)
			lower_code = e.code.lower()
			if lower_code in mappings:
				callbacks = mappings[lower_code]
				state = bool(e.state)
				if state in callbacks and callbacks[state] is not None:
					callbacks[state]()

if __name__ == "__main__":
	main()
