from ipywidgets import widgets
from IPython.display import display, Markdown, Latex
from IPython.core.display import HTML, Javascript

import re

import os
import json
import requests
import sys

import time

import IPython
from IPython.lib import kernel
from notebook.notebookapp import list_running_servers

def get_notebook_name():
    connection_file_path = kernel.get_connection_file()
    connection_file = os.path.basename(connection_file_path)
    kernel_id = connection_file.split('-', 1)[1].split('.')[0]
    
    servers = list(list_running_servers())
    
    nb_name = None
    
    for s in servers:
        try:
            sessions = requests.get('%sapi/sessions?token=%s' % (s['url'], s['token'])).json()
        except:
            continue
            
        for sess in sessions:
            if sess['kernel']['id'] == kernel_id:
                nb_name = os.path.basename(sess['notebook']['path'])
                break
            
    return nb_name

def get_answers_df(f):
    df = pd.read_csv(f, dtype={ 'student': str })
        
    df.set_index(['student', 'question'], inplace=True)
    df.sort_index(level=0, inplace=True)

    return df
    
def save_answers_df(f, df):
    df.to_csv(f, encoding='utf8')

def load():
    display(HTML("""<style>
        h4 {
            margin-top: 20px;
        }
    
        .widget-area .prompt .close {
            display: none !important;
        }
    
        .widget-label, .spec-label {
            color: #666;
            font-weight: bold;
            
            min-width: 180px !important;
        }
        
        .widget-textarea {
            width: 750px;
        }
        
        .teacher-answer {
            font-size: 14pt;
            color: #134596;
        }
        
        .jupyter-widgets-view {
            border-top: 1px solid #ccc;
            border-bottom: 1px solid #ccc;
        }
        
        .exam-message {
            font-size: 12pt;
            line-height: 1.2; 
            
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .exam-message small {
            font-size: 10pt;
        }
        </style>"""))
    
    if not fail:
        display(HTML("""<script>
        var executed = false
    
        var runAndHide = function() {
            var q_indexes = []
            $('.input_area').each(function(i, area) {
                area = $(area)
    
                if(area.text().indexOf('questions.ask') > -1) {
                    area.parents('.input').hide()
    
                    if(!executed) {
                        var index = $('.cell').index(area.parents('.cell'))
    
                        if(index != -1) {
                            q_indexes.push(index)
                        }
                    }
                }
            })
    
            if(!executed) {
                IPython.notebook.execute_cells(q_indexes)
                executed = true
            }
        }
    
        runAndHide()
    
        setInterval(runAndHide, 200)
    
        setInterval(function() {
            $('.widget-text input[type="text"], .widget-textarea textarea').unbind('keydown')
            $('.widget-text input[type="text"], .widget-textarea textarea').on('keydown', function(e) {
                if((e.metaKey || e.ctrlKey) && e.keyCode == 83) {
                    IPython.notebook.save_checkpoint()
    
                    e.preventDefault();
                    return false;
                }
            })
        }, 5000)
        </script>"""))

def create_input(q, textarea=False, code=False):
    if role == 'student':
        if not code:
            if textarea:
                w = widgets.Textarea(
                    placeholder='Vul in...',
                    value=answers[q]['answer']
                )
            else:
                w = widgets.Text(
                    placeholder='Vul in...',
                    value=answers[q]['answer']
                )
            
            w.question = q
            w.observe(answer_changed)
        else:
            w = widgets.HTML('')
    else:
        if len(answers[q]['answer'].strip()):
            answer = answers[q]['answer'].replace('\n', '<br />')
        else:
            if code:
                answer = '<em style="color: #ccc; font-size: 12pt; margin-bottom: -2px;">Code:</em>'
            else:
                answer = '<em style="color: #ccc;">Geen antwoord</em>'
        
        w = widgets.HTML("<span class='teacher-answer'>%s</span>" % answer)

    return w

def answer_changed(change):
    if change['name'] == 'value':
        q = change.owner.question
        answers[q]['answer'] = change.new
        
        save_answers()

def score_changed(change):
    if role == 'teacher':
        if change['name'] == 'value':
            q = change.owner.question
            
            if len(str(change.new)):
                new = change.new.replace(',', '.')
            
                try:
                    new = float(new)
                except:
                    new = np.nan
            else:
                new = np.nan
                
            answers[q]['score'] = new
            answers_df = get_answers_df(student_answers)
            
            #answers_df.set_value((student_id, q), 'score', new)
            answers_df.at[(student_id, q), 'score'] = new
            
            save_answers_df(student_answers, answers_df)
        
def save_answers():
    if answer_file:
        with open(answer_file, 'w') as f:
            json.dump(answers, f)

def get_answers():
	return answers

def pretty_print_answers():
    for i, (q, a) in enumerate(answers.items()):
        display(Markdown('#### '+ str(i + 1) +'. '+ q))
        display(Markdown('*'+ a['answer'] +'*'))

def ask(qid):
    def isfloat(value):
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    question = questions_map[qid]

    if 'answer-spec' in question and not ('type' in question['properties'] and question['properties']['type'] == 'open'):
        X = answers[qid]['answer']

        r = False
        try:
            r = eval(question['answer-spec'])
        except:
            pass

        if r:
            #if 'points' in question['properties']:
            #    points = float(question['properties']['points'])
            #else:
            #    points = 1

            #answers[qid]['score'] = points
            color = 'green'
        else:
            #answers[qid]['score'] = 0
            color = 'red'

        # save_answers()

        spec_label = 'Test'

        spec_html = '''<div style="margin-top: -3px;"><span class="spec-label">'''+ spec_label +'''</span>:&nbsp;&nbsp;<pre style="display: inline; color: '''+ color +'''">'''+ question['answer-spec'] +'''</pre></div>'''

        answer_spec = widgets.HTML(value=spec_html)
        score_description = 'Score (maximaal '+ str(question['properties']['points']) +'):'
    else:
        color = 'black'
        answer_spec = None

        if 'points' in question['properties']:
            score_description = 'Score (maximaal '+ str(question['properties']['points']) +'):'
        else:
            score_description = 'Score:'

    if role == 'teacher':
        if len(str(answers[qid]['score'])):
            if int(answers[qid]['score']) != float(answers[qid]['score']):
                score = str(float(answers[qid]['score']))
            else:
                score = str(int(answers[qid]['score']))
        else:
            score = ''
    
        score_field = widgets.Text(
            description=score_description,
            placeholder='0',
            value=score
        )
        score_field.question = qid
        score_field.observe(score_changed)

        score_field.layout.width = '235px'
        score_flex = widgets.HBox([score_field])
        score_flex.layout.justify_content = 'flex-end'

        if answer_spec:
            answer_flex = widgets.HBox([answer_spec])
            answer_flex.layout.justify_content = 'flex-end'

            answer_spec_score = widgets.VBox([answer_flex, score_flex])
        else:
            answer_spec_score = score_flex
    else:
        if 'points' in question['properties']:
            points = question['properties']['points']
        else:
            points = '1'

        answer_spec_score = widgets.HTML(value='<span style="color: #666;"><strong>%s</strong> / %d punten</span>' % (points, total_points))

    if 'type' in question['properties'] and question['properties']['type'] == 'open':
        
        field = create_input(qid, code=True)
        
        if 'answer-spec' in question:
            spec_label = 'Richtlijn'
            spec_html = '''<div style="margin-top: 6px;"><span class="spec-label">'''+ spec_label +'''</span>:&nbsp;&nbsp;<pre style="display: inline;">'''+ question['answer-spec'] +'''</pre></div>'''

            widget = widgets.HBox([field, widgets.VBox([widgets.HTML(value=spec_html), score_flex])])
            widget.layout.justify_content = 'space-between'
        else:
            widget = widgets.HBox([field, answer_spec_score])
            widget.layout.justify_content = 'space-between'

    else:
        if 'type' in question['properties'] and question['properties']['type'] == 'long':
            field = create_input(qid, textarea=True)
        else:
            field = create_input(qid)

        widget = widgets.HBox([field, answer_spec_score])
        widget.layout.justify_content = 'space-between'

    display(widget)

if 'STUDENT_QUESTIONS_FILE' in os.environ:
    questions_file = os.environ['STUDENT_QUESTIONS_FILE']
elif os.path.exists('questions.json'):
    questions_file = 'questions.json'
else:
    questions_file = None

if 'STUDENT_ANSWERS_FILE' in os.environ:
    answer_file = os.environ['STUDENT_ANSWERS_FILE']
elif os.path.exists('answers.json'):
    answer_file = 'answers.json'
else:
    answer_file = 'answers.json'

if 'TEACHER_ANSWER_MODEL' in os.environ:
    answer_model = os.environ['TEACHER_ANSWER_MODEL']
elif os.path.exists('answer-model.json'):
    answer_model = 'answer-model.json'
elif os.path.exists('../answer-model.json'):
    answer_model = '../answer-model.json'
else:
    answer_model = None
    
if os.path.exists('student-answers.csv'):
    student_answers = 'student-answers.csv'
else:
    student_answers = None
  
fail = False  
if answer_model and not student_answers:
    display(widgets.HTML('<div class="exam-message"><strong style="color: darkred;">Er is een antwoordmodel gevonden, maar geen bestand met antwoorden van studenten.</strong><br /><small>Er kan niet worden nagekeken.</small></div>'))
    
    fail = True

if student_answers and not answer_model:
    display(widgets.HTML('<div class="exam-message"><strong style="color: darkred;">Er is een bestand met antwoorden van studenten gevonden, maar geen antwoordmodel.</strong><br /><small>Er kan niet worden nagekeken.</small></div>'))
    
    fail = True

if not fail:
    if answer_model:
        questions = json.load(open(answer_model))
    
        role = 'teacher'
    else:
        questions = json.load(open(questions_file))
    
        role = 'student'
    
    questions_map = { q['id']: q for q in questions }
    
    total_points = 0
    for q in questions:
        if 'points' in q['properties']:
            total_points += float(q['properties']['points'])
        else:
            total_points += 1
    
    if student_answers:
        import pandas as pd
        import numpy as np
    
        student_answers_df = get_answers_df(student_answers)
        
        student_id = str(get_notebook_name().split('.')[0].split('_')[-1])
    
        display(widgets.HTML('<div class="exam-message">Het volgende student ID is gedetecteerd: <strong>%s</strong><br /><small>Verifi&euml;er of dit correct is.</small></div>' % student_id))
        
        if os.path.exists('auto-scoring-done'):
            display(widgets.HTML('<div class="exam-message"><strong style="color: darkgreen;">Auto-scoring is uitgevoerd.</strong><br /><small>Automatisch ingevulde scores mogen overschreven worden.</small></div>'))
        else:
            display(widgets.HTML('<div class="exam-message"><strong style="color: darkred;">Auto-scoring is nog niet uitgevoerd.</strong></div>'))
        
        answers = student_answers_df.loc[student_id].fillna('').to_dict(orient='index')
    else:
        if os.path.isfile(answer_file):
            with open(answer_file) as f:
                answers = json.load(f)
        else:
            answers = { q['id']: { 'answer': '' } for q in questions }
            
            save_answers()