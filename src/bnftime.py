'''
    NLP_datetime_parser
    
    The base idea of this scripts, is extracted from 
    http://pyparsing.wikispaces.com/UnderDevelopment#x-Time expression parser
    examples in the pyparsing tool webpage. 
    
    This scripts allows to parse range of dates from|until, expressed as 
    natural language phrases. It is extendible through a JSPON calendar,
    and is a prototype of for a future library.
    
    MIT License
    Copyright (c) 2009 Luciano M. Guasco

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
'''

# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pyparsing import *
import json

'''
This module contains the basic classes and components to provide a dates parser. 
The idea of the parser is to detect dates and lapses of time, expressed in natural language
and transformed to a dictionary {"from":date,"to":date}.
Its based on a BNF, expressed with pyparsing
'''

class Calendar(object):
    '''Calendar is the class responsible of reading a json structure and create a calendar for 
    the language specified in the constractor (spanish default). This calendar contains information
    about expressions ("christmas", "new years eve",etc.), names for days, months and limits for years, etc.
    '''

    def __init__(self,lang='es'):
        self.lang = lang
        self.calendar = {}
        try:
            json_data=open('../data/calendar.json')
            data = json.load(json_data)
            self.calendar = data[self.lang]
        except:            
            print 'impossible to load data/calendar.json'        
    
    def get_days(self):
        return self.calendar["days"]
    
    def get_months(self):
        return self.calendar["months"]
    
    def get_holidays(self):
        return self.calendar["holidays"]
    
    def get_grammar(self,key):
        return self.calendar["grammar"][key]
    
    def get_offset_day_point(self,day_point):
        for dic_daypoints in self.calendar["daypoint_offsets"].values():
            if day_point in dic_daypoints["expr"]:
                return dic_daypoints["offset"]
        return 0
            
    def get_time_units(self,timeunit): 
        for key_timeunits in self.calendar["units"].keys():
            if timeunit in self.calendar["units"][key_timeunits]["expr"]:
                return key_timeunits
    
    
    def get_expr_from_calendar(self,key):
        expressions = []
        holidays = self.calendar[key]
        for val in holidays.values():
            expressions.extend(val["expr"]) 
        return expressions
    

class TimeGrammar(object):
    '''
    TimeGrammar class is responsible of creating an instance of Calendar, based on specified language. 
    It creates a grammar that will be used to parse expressions and detect the interesting parts. 
    The main method is parse, which takes an expression and the internal grammar and derives it extracting useful 
    information returned as a dictionary {from:date,to:date}
    '''

    def __init__(self,lang="es"):
        self.lang = lang
        self.calendar  = Calendar(self.lang)
        self.init_grammar()

    #extract the calcualtedTime given the absTime.   
    def calculate_time(self,toks):
        if toks.absTime:
            absTime = toks.absTime
        else:
            absTime = datetime.now()
        if toks.mesOffset:
            try:
                absTime +=relativedelta(month = +toks['mesOffset'])
            except:
                print 'error adding month'
        elif toks.timeOffset:
                absTime += toks.timeOffset
        toks["calculatedTime"] = absTime
    # string conversion parse actions
    
    #calculates a specific date for a given element: name day, or time point such as now, yesterday, etc.
    def calc_day(self,toks):
        now = datetime.now()
        if toks.dian:
            todaynum = now.weekday()
            daynames = self.calendar.get_days()
            namedaynum = daynames.index(toks.dian.lower())
            daydiff = (namedaynum + 7 - todaynum) % 7
            toks['absTime'] = datetime(now.year, now.month, now.day)+timedelta(daydiff)
        
        elif toks.dia_point:
            dia_point = toks.dia_point.lower()
            offset = self.calendar.get_offset_day_point(toks.dia_point)
            toks["absTime"] = datetime(now.year, now.month, now.day) + timedelta(offset)
       
        elif toks.numerico:          
            if toks.numerico.dia:              
                dia = toks.numerico.dia
            else:
                 dia = 01
            if toks.numerico.mes:
                mes = toks.numerico.mes
            else:
                mes = now.month
            if toks.numerico.anio:
                anio = toks.numerico.anio
            else:
                anio = now.year
            toks["absTime"] = datetime(anio,mes,dia)
    
    def calc_lapse_of_time(self,toks):
        #if toks.absTime it means is alraedy calculated, 
        # in case of para dentro de 2 lunes [unit no hay]
        if not toks.absTime:                
            unit = self.calendar.get_time_units(toks.timeunit)        
            td = {        
                'week' : timedelta(7),
                'day'    : timedelta(1),
                'month':   1
            }[unit]
            #qty transformation (as instance: three weeks, 3*timedelta(7)
            if toks.qty:
                    td *= int(toks.qty)                
            if unit == 'month': #unit = month
                toks["mesOffset"] = int(toks.qty)           
            else:
                toks["timeOffset"] = td
        else:            
            if toks.qty:                
                toks["absTime"] = toks["absTime"] + (int(toks.qty) * timedelta(7))
                    
    #calculates a range of dates for a given expresion such as christmas, new year, etc.
    def calc_expression(self,toks):      
                
        def calc_general_expr(toks,expression):
            now = datetime.now()            
            date_begin = datetime(now.year, expression["dates_begin"][0],expression["dates_begin"][1]) 
            date_end = datetime(now.year, expression["dates_end"][0],expression["dates_end"][1]) 
            
            if now > date_begin:
                if now > date_end:
                    raise Exception('date is past')
                else:
                    #now is begin the date of expression, lets asume is for next year.
                    date_begin += relativedelta(years =+1)
                    date_end += relativedelta(years =+1)                                           
            toks['desde'] = date_begin
            toks['hasta'] = date_end
            
        def calc_finde(toks):
            now = datetime.now()
            todaynum = now.weekday()
            if todaynum > 4: 
                now = now + timedelta(2)
                todaynum = now.weekday()
            fromDay = now + timedelta( (4 + 7 - todaynum) % 7 )
            toDay   = now + timedelta( (6 + 7 - todaynum) % 7 )
            
            toks['desde'] = fromDay
            toks['hasta'] = toDay
        
        #BEGIN METHOD
        holidays = self.calendar.get_holidays()
        expression = ""
        for key_holidays in holidays.keys():
            if toks.expr in holidays[key_holidays]["expr"]:
                expression = key_holidays
                break
        try:    
            if expression == "weekend":
                calc_finde(toks)
            else:
                calc_general_expr(toks,holidays[expression])
        except:
            toks['desde'] = 'past'
            toks['hasta'] = 'past'
     
     #Unification of 'self.DESDE' 'self.HASTA' values in one result dictionary.        
    def unify_result(self,toks):
        #if toks['self.DESDE'] > toks['self.HASTA'] :
        #    toks['self.HASTA'] = toks['self.HASTA'] + timedelta(7)
        toks['res'] = {'desde': toks['desde'],'hasta':toks['hasta']}
        
             
    #Store just the datetime value in 'self.DESDE', 'self.HASTA' instead of result object
    
    def extract_calculated_time(self,toks):
        if toks.desde:
            toks['desde'] = toks['desde'].calculatedTime            
        if toks.hasta:
            toks['hasta'] = toks['hasta'].calculatedTime
    
    def calc_month(self,toks):      
        monthnames = self.calendar.get_months()
        if toks[0].lower() in monthnames:
            monthnamenr = monthnames.index(toks[0].lower()) + 1
            return monthnamenr
        else:
            return 0
        
    def calc_anio(self,toks):
        anio = int(toks[0])
        if anio <100:
            return (datetime.now().year/100)* 100 + anio
        else:
            return anio
    
    def init_grammar(self):
        #CaseLess operator
        cl = CaselessLiteral
        
        #The grammar
        
        #lunes, martes, miercoles...
        self.DIA_WORD = oneOf(self.calendar.get_days())("dian")
        self.DIA_WORD.addParseAction(self.calc_day)
        
        #hoy, ayer, manhana
        self.DIA_POINT = oneOf(self.calendar.get_expr_from_calendar("daypoint_offsets"))("dia_point")
        self.DIA_POINT.addParseAction(self.calc_day)
     
        # Section: DIA SEP MES SEP ANIO  
        #2011, dos mil once
        self.ANIO = Word(nums,min=2,max=4).setParseAction(self.calc_anio) 
        
        #03, marzo
        self.MES = oneOf(self.calendar.get_months()).addParseAction(self.calc_month) | Word(nums,max=2).setParseAction(lambda t:int(t[0]))
        #de, del, /
        self.SEP_FECHA = oneOf(self.calendar.get_grammar("separators"))
        
        self.DIA = Word(nums,max=2).setParseAction(lambda t:int(t[0]))
        
        self.NUMERICO = Group(Optional(self.DIA)('dia') + Optional(self.SEP_FECHA) + Optional(self.MES)('mes') + Optional(self.SEP_FECHA) + Optional(self.ANIO)('anio'))('numerico')
        self.NUMERICO.addParseAction(self.calc_day)
        
        self.NUMERO = Word(nums).setParseAction(lambda t:int(t[0]))
        
        self.UNIDAD = oneOf(self.calendar.get_expr_from_calendar("units"))
      
        self.LAPSO =  oneOf(self.calendar.get_grammar("lapse"))
        
        self.TEMPORAL = Optional(self.LAPSO) + self.NUMERO('qty') + self.UNIDAD('timeunit') | Optional(self.LAPSO) + Optional(self.NUMERO('qty')) +self.DIA_WORD('dian')
        self.TEMPORAL.addParseAction(self.calc_lapse_of_time)
        
        #Fin de Section
        
        self.FECHA =  self.DIA_WORD | self.DIA_POINT | self.TEMPORAL | self.NUMERICO
        self.FECHA.addParseAction(self.calculate_time)
        
                
        self.EXPRESSION = oneOf(self.calendar.get_expr_from_calendar("holidays"))('expr') 
        self.EXPRESSION.addParseAction(self.calc_expression,self.unify_result)
        
        self.DESDE_WORDS = oneOf(self.calendar.get_grammar("from"))
        self.DESDE = self.DESDE_WORDS + Optional(cl("el")) + self.FECHA
        self.DESDE.addParseAction(self.extract_calculated_time)
        
        #esta regla parsea: 
        self.HASTA_WORDS = oneOf(self.calendar.get_grammar("to"))
        self.HASTA = self.HASTA_WORDS + Optional(cl("el")) + self.FECHA
        self.HASTA.addParseAction(self.extract_calculated_time)
        
        #self.DESDE self.HASTA
        #esta regla parsea: self.DESDE self.FECHA self.HASTA self.FECHA
        self.DESDE_HASTA = self.DESDE('desde') + self.HASTA('hasta') 
        #dp = self.FECHA.setResultsName('self.DESDE') +'por'+ cant('qty') + relativeTimeUnit
        self.DESDE_HASTA.addParseAction(self.unify_result)
        
        self.RANGO = self.DESDE_HASTA | self.EXPRESSION 
        
        #| self.LAPSO

    def parse(self,query):
        rg = self.RANGO.scanString(query) 
        for tokens, start,end in rg:  
            try:
                return {'desde':tokens['res']['desde'].date().__str__(),
                        'hasta':tokens['res']['hasta'].date().__str__()
                        }
            except:
                return{'desde':'pasado',
                       'hasta':'pasado'
                       }
        return {'desde':'',
                'hasta':''
                }
   
class ParserTest():
    '''This class is the wrapper for testing the parser, with data and language provided in the constructor. '''

    def __init__(self,data,language):
        self.expressions = data['expressions']
        self.lapses = data['lapses']
        self.dates = data['dates']
        self.lang = language

    def test(self):
        parser = TimeGrammar(self.lang)
        for expr in self.expressions:
            print 'Evaluating: {0}\n'.format(expr)
            print 'Result: {0}\n'.format(parser.parse(expr))

if __name__ == '__main__':
        
        test = """\
        this is a range from today until tomorrow
        this is a range from 25 febraury until 28 febraury
        this is a range from next weekend  until 30 march
        this is a range for christmas
        """
        tests = {'expressions' : test.split("\n"),'lapses' : [],'dates' : []}
        tester = ParserTest(tests,"en")
        tester.test()
