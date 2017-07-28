'''
Created on 27 Jul 2017

@author: nick
'''

import re, pyparsing as pp, pprint, tests

#pp.ParserElement.enablePackrat()



re_func=re.compile("(func|function)")
re_proc=re.compile("(proc|procedure)") 
re_class=re.compile("class")
re_select=re.compile("[ \t]select[ \t]")
re_update=re.compile("[ \t]update[ \t]")
re_comment=re.compile("--.*")

#------------------------------------------------------------------------------------------------------------     
# grammar definition
#------------------------------------------------------------------------------------------------------------     

# literals and keywords 
OPB=pp.Literal("(") 
CLB=pp.Literal(")") 
WITH=pp.Keyword("with")
NULL=pp.Keyword("null")
WITHNULL=pp.originalTextFor(WITH+NULL)
IS=pp.Keyword("is").suppress()
LARGE=pp.Keyword("large")
SMALL=pp.Keyword("small")
NUMBER=pp.Keyword("number")
LARGENUMBER=pp.originalTextFor(LARGE+NUMBER)
SMALLNUMBER=pp.originalTextFor(SMALL+NUMBER)
STRING=pp.Keyword("string")
BOOLEAN=pp.Keyword("boolean")
DATE=pp.Keyword("date")
TEXT=pp.Keyword("text")
ARRAY=pp.Keyword("array")
RETURNS=pp.Keyword("returns")
PUBLIC=pp.Keyword("public") 
VIRTUAL=pp.Keyword("virtual") 
FUNC=pp.oneOf("func function") 
PROC=pp.oneOf("proc procedure") 
FUNC=FUNC.setResultsName("function")
PROC=PROC.setResultsName("procedure")
OF=pp.Keyword("of")
SELECT=pp.Keyword("select")
UPDATE=pp.Keyword("update")
FROM=pp.Keyword("from")
AS=pp.Keyword("as")
EQ=pp.Literal("=")
ONE=pp.Keyword("one")
STAR=pp.Literal("*")
UNIQUE=pp.Keyword("unique")
CLASS=pp.Keyword("class")

#variable/label name
name=pp.Word(pp.alphanums+"_"+".")
name.setName("name")

#sql 
astuple=AS+name 
tablename=(pp.Optional(name+EQ).suppress()+name )
tablename=tablename.setResultsName("tablename")
tablefield=pp.Word(pp.alphanums+"_"+".")
tablefields=pp.Optional(tablefield ^ pp.delimitedList(tablefield,","))

#class   
pptype=pp.Word(pp.alphanums+".")
classname=pp.Word(pp.alphanums+"_")
classname=classname.setResultsName("classname") 

# function/proc name 
callname=pp.Word(pp.alphanums+"_")
callname=callname.setResultsName("callname")

# parameter compounds 
types=(NUMBER ^ LARGENUMBER ^ SMALLNUMBER ^ STRING ^ TEXT ^ DATE ^ BOOLEAN ^ pptype)
DEFARRAY=ARRAY+OF+types
paramtype=pp.Group( (types ^ DEFARRAY) + pp.Optional(WITHNULL))
param= name + IS + paramtype
param.setName("param")
param_list=pp.Group( OPB + pp.Optional(pp.delimitedList(param, ",")) + CLB)
param_list.setName("param_list")
param_list=param_list.setResultsName("parameter_list")

# return type compounds 
single_ret=paramtype.copy() 
multi_ret=OPB + pp.delimitedList(paramtype,",") + CLB
returntypes=single_ret #(multi_ret ^ single_ret)
returntypes=returntypes.setResultsName("return_types")

# top level parsers

classdef = pp.Optional(PUBLIC)+ \
        CLASS + \
        classname + \
        pp.SkipTo("{",include=True )
        
function= pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        FUNC + \
        callname+ \
        param_list + \
        RETURNS + \
        returntypes +\
        "{"

procedure=pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        PROC + \
        callname+ \
        param_list + \
        "{"

select=SELECT+ \
        pp.SkipTo(FROM,True) + \
        tablename+ \
        pp.SkipTo("{",include=True)
        
update=UPDATE+ \
        pp.Optional(astuple)+ \
        tablename+ \
        pp.SkipTo("{", include=True)

[ f.parseWithTabs() for f in [ function, procedure, select, update, classdef ]]
 
#------------------------------------------------------------------------------------------------------------     
def get_to_matching_brace(code_block):
    
    br=1
    st=0
    en=0
    while True:
        if code_block[en]=="{":
            br+=1
        if code_block[en]=="}": 
            br-=1
        if br==0:
            return code_block[st:en+1],code_block[en+1:]
        en+=1

#------------------------------------------------------------------------------------------------------------     
def process(parsers,code_block,parent):
      
    out=[]
    
    while len(code_block)>0:
        line=code_block.splitlines()[0]
        line=re_comment.sub("",line)
        
        match=0
        if re_class.search(line):
            
            for toks,start,end in parsers["classdef"].scanString(code_block):
                matched=code_block[start:end]            
                out.append(code_block[0:start]+matched)     #keeps indent 
                code_block=code_block[end:]
                namespace=parent+"."+str(toks["classname"])
                body,rest=get_to_matching_brace(code_block)
                code_block=rest 
                out.append(process(parsers,body,namespace))
                match=1
                break
            
        elif re_func.search(line):

            for toks,start,end in parsers["function"].scanString(code_block):
                matched=code_block[start:end]            
                out.append(code_block[0:start]+matched)     #keeps indent 
                code_block=code_block[end:]
                namespace=parent+"."+str(toks["callname"])
                out.append( namespace + str(toks["parameter_list"]) + str(toks["return_types"]))
                body,rest=get_to_matching_brace(code_block)
                code_block=rest 
                out.append(process(parsers,body,namespace))
                match=1
                break
            
        elif re_proc.search(line):
 
            for toks,start,end in parsers["procedure"].scanString(code_block):
                matched=code_block[start:end]
                out.append(code_block[0:start]+matched)     #keeps indent 
                code_block=code_block[end:]
                namespace=parent+"."+str(toks["callname"])
                out.append( namespace + str(toks["parameter_list"]))
                body,rest=get_to_matching_brace(code_block)
                code_block=rest
                out.append(process(parsers,body,namespace))
                match=1
                break     
            
        elif re_select.search(line):

            for toks,start,end in parsers["select"].scanString(code_block):
                matched=code_block[start:end]
                out.append(code_block[0:start]+matched)     #keeps indent 
                code_block=code_block[end:]
                namespace=parent+"."+str(toks["tablename"][0])
                out.append( namespace + " select" )
                body,rest=get_to_matching_brace(code_block)
                code_block=rest
                out.append(process(parsers,body,namespace))
                match=1
                break
                    
        elif re_update.search(line):

            for toks,start,end in parsers["update"].scanString(code_block):
                matched=code_block[start:end]
                out.append(code_block[0:start]+matched)     #keeps indent 
                code_block=code_block[end:]
                namespace=parent+"."+toks["tablename"]
                out.append( namespace + " update" )
                body,rest=get_to_matching_brace(code_block)
                code_block=rest
                out.append(process(parsers,body,namespace))
                match=1
                break     
            
        if match==0:
            out.append(line)
            code_block="\n".join(code_block.splitlines()[1:])
   
    return "\n".join(out)
    
#------------------------------------------------------------------------------------------------------------
myfile="request.v"
textfile=open(myfile,"r")
text=textfile.read()
namespace=myfile.split(".")[0]

parsers={ 
          "function"   : function,
          "procedure"  : procedure,
          "select"     : select,
          "update"     : update,
          "classdef"   : classdef 
        }

res=process( parsers, text, namespace)
with open("parse.out","w") as outf:
    print >>outf,res 

print res 





   