'''
Created on 27 Jul 2017

@author: nick
'''
#------------------------------------------------------------------------------------------------------------     
import re, pyparsing as pp    #, tests
from optparse import OptionParser 
#------------------------------------------------------------------------------------------------------------     

tracecall='call debug.DebugNL(("%s",%s))'
printables={}
for i in ["small number","large number","number","string","boolean","date","time","money","text" ]:
    printables[i]=True 
debugmode=False 

#------------------------------------------------------------------------------------------------------------     
# regexp defs
#------------------------------------------------------------------------------------------------------------     

re_class=re.compile("(public class|class)")
re_select=re.compile("[ \t]select[ \t]")
re_update=re.compile("[ \t]update[ \t]")
re_comment=re.compile("--.*")
re_return=re.compile("[ \t]return[ \t$\(]")
re_line=re.compile("@line@")
re_remove_list=re.compile("[\[\]']")

#------------------------------------------------------------------------------------------------------------     
# pyparsing grammar definition 
#------------------------------------------------------------------------------------------------------------     

# literals and keywords 
OPB=pp.Literal("(").suppress()
CLB=pp.Literal(")").suppress()
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
RETURN=pp.Keyword("return")
RETURNS=pp.Keyword("returns")
PUBLIC=pp.Keyword("public") 
VIRTUAL=pp.Keyword("virtual") 
FUNC=pp.oneOf("func function") 
PROC=pp.oneOf("proc procedure") 
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

#sql 
astuple=AS+name 
select_tablename=(pp.Optional(name+EQ).suppress()+name ).setResultsName("select")
update_tablename=(pp.Optional(name+EQ).suppress()+name ).setResultsName("update")
tablefield=pp.Word(pp.alphanums+"_"+".")
tablefields=pp.Optional(tablefield ^ pp.delimitedList(tablefield,","))

#class   
pptype=pp.Word(pp.alphanums+".")
classname=pp.Word(pp.alphanums+"_").setResultsName("class") 

# function/proc name 
funcname=pp.Word(pp.alphanums+"_").setResultsName("function")
procname=pp.Word(pp.alphanums+"_").setResultsName("procedure")

# parameter compounds 
types=(NUMBER ^ LARGENUMBER ^ SMALLNUMBER ^ STRING ^ TEXT ^ DATE ^ BOOLEAN ^ pptype)
DEFARRAY=ARRAY+OF+types
paramtype=pp.Group( (types ^ DEFARRAY) + pp.Optional(WITHNULL))
param= (name + IS + paramtype) 
param_list=pp.Group( OPB + pp.Optional(pp.delimitedList(param, ",")) + CLB).setResultsName("parameter_list") 

# return compounds 
single_ret=paramtype
multi_ret=OPB + pp.delimitedList(paramtype,",") + CLB
returntypes=pp.Group(multi_ret ^ single_ret).setResultsName("return_types")
returnvalues=pp.SkipTo("}",include=True).setResultsName("return_values") 

simple_return=name+pp.ZeroOrMore(pp.Suppress(",")+name)

#------------------------------------------------------------------------------------------------------------     
# top level parsers.  the quick_ variants are for fast checking of the current 3 line code window 
#------------------------------------------------------------------------------------------------------------     

class_ = pp.Optional(PUBLIC)+ \
        CLASS + \
        classname + \
        pp.SkipTo("{",include=True )

quick_function = pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        FUNC
        
function= pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        FUNC + \
        funcname+ \
        param_list + \
        RETURNS + \
        returntypes +\
        "{"
        
return_=RETURN +\
         returnvalues
 

quick_procedure=pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        PROC 
        
procedure=pp.Optional(PUBLIC) + \
        pp.Optional(VIRTUAL) + \
        PROC + \
        procname+ \
        param_list + \
        "{"

select=SELECT+ \
        pp.SkipTo(FROM,True) + \
        select_tablename+ \
        pp.SkipTo("{",include=True)
        
update=UPDATE+ \
        pp.Optional(astuple)+ \
        update_tablename+ \
        pp.SkipTo("{", include=True)

[ f.parseWithTabs() for f in [ function, procedure, return_, select, update, class_ ]]

#------------------------------------------------------------------------------------------------------------     
#------------------------------------------------------------------------------------------------------------  
def debug(txt):
    if debugmode:
        print txt      
        
#------------------------------------------------------------------------------------------------------------     
def def_trace(which, name, param_list, return_types ):
    
    # returns 4gl trace call statement to add to the .v 
    # line numbers will be substituted once we've finished the main processing
    # easier that way with all the recursion going on....
    
    module=name.split(".")[0]+".v"
    where=".".join(name.split(".")[1:]) 
    
    strings={
             "procedure" : "%s : line %s : %s %s " % (module,"@line@",which,where),
             "function"  : "%s : line %s : %s %s " % (module,"@line@",which,where),
             "select"    : "%s : line %s : %s %s " % (module,"@line@",where,which),
             "update"    : "%s : line %s : %s %s " % (module,"@line@",where,which),
             "return"    : "%s : line %s : return from %s " % (module,"@line@",where),
             }
    
    if not which in strings:
        return ""
    
    p1=strings[which]
    p2=""
    
    if which in ("function","procedure"):
        
        # parameter values 
        
        param_count=len(param_list)/2
        for i in range(0,param_count):
            param_name=param_list[i*2]
            param_type=param_list[i*2+1]
            p1+="[<>]" 
            # only attempt to trace basic types. dont trace if "with null" 
            if len(param_type)==1 and param_type[0] in printables:
                p2+=param_name+","  
            else:
                p2+='"_",'
        
        if len(p1)>0 and p1[-1]==",":
            p1=p1[:-1]
        if len(p2)>0 and p2[-1]==",":
            p2=p2[:-1]
              
    elif which=="return":
        
        # return values. only trace them if we have a simple value or tuple of values.
        # no expressions or function calls allowed. 
        
        try:
            res=simple_return.parseString(param_list)
            for n,t in enumerate(return_types ):
                if t[0] in printables:
                    if n < len(res):
                        if res[n]=="null":
                            p1+="[null]"
                        else:
                            p1+="[<>]"
                            p2+=res[n]+","
                else:
                    p1+="[<>]"
                    p2+='"_"'
            
            # bin the last comma
            if len(p2)>0 and p2[-1]==",":
                p2=p2[:-1]
                     
        except:
            # match failed
            pass
        
    else:
        
        # sql statements. nothing to add 
        
        p1+="<>"
        p2+='""'
                
    return tracecall % (p1,p2)

#------------------------------------------------------------------------------------------------------------
def mystr(item):    
    return re_remove_list.sub("",str(item))

#------------------------------------------------------------------------------------------------------------
def check_func(line):
    
    try:
        quick_function.parseString(line)
        return True
    except:
        return False 
#------------------------------------------------------------------------------------------------------------
def check_proc(line):
    
    try:
        quick_procedure.parseString(line)
        return True
    except:
        return False 
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
            body=code_block[st:en+1]
            rest=code_block[en+1:]
            return body,rest
        en+=1

#------------------------------------------------------------------------------------------------------------     
def check(window):
    
    # quick searches on the current source window to see if we're at a class/proc/func/select etc 
    
    line0=re_comment.sub("",window[0])
    line="".join([ re_comment.sub("",i) for i in window ])
    
    if re_class.search(line):
        return "class"
    elif check_func(line):
        return "function"
    elif check_proc(line):
        return "procedure"
    elif re_return.search(line0):
        return "return"
    elif re_select.search(line0):
        return "select" 
    elif re_update.search(line0):
        return "update"
    
    return None 
#------------------------------------------------------------------------------------------------------------     
def process(parsers,parent,code_block,parent_name,parent_ret_types):
    
    '''  
    check a three line lookahead from the current line for class|function|procedure defs 
    or the current line for return|select|update statements
    for speed, function and procedure checks use a small parser, rest use regexps 
    if match found, run it through the relevant full parser to pull out the required items so we can insert a trace line 
    to the outputted code 
    '''
    
    out=[] 
    debug("%s %s " % (parent,parent_name))
    
    while len(code_block)>0:
       
        ln=len(code_block)       
        window_length = 3 if ln>2 else ln
        window=code_block.splitlines()[0:window_length]
        debug(">"+window[0])
        match=0
        
        line_match=check(window)
        if line_match != None: 
            
            debug(parent+"|"+line_match)
            
            if line_match == "return" :
                if parent=="function": 
                    for parse_result,start,end in parsers[line_match].scanString(code_block):
                        matched=code_block[start:end]   
                        ret_values=parse_result["return_values"] 
                        out.append(def_trace(line_match,parent_name,ret_values,parent_ret_types))         
                        out.append(code_block[0:start]+matched)     #keeps indent 
                        code_block=code_block[end:]
                        namespace=parent_name
                        match=1
                        break
            
            else:
                 
                for parse_result,start,end in parsers[line_match].scanString(code_block):
                    matched=code_block[start:end]            
                    out.append(code_block[0:start]+matched)     #keeps indent 
                    code_block=code_block[end:]
                    dot="->" if parent=="class" else "."
                    namespace=parent_name+dot+mystr(parse_result[line_match])
                    params=parse_result["parameter_list"] if line_match in ("procedure","function") else None
                    out.append(def_trace(line_match,namespace,params,None))
                    ret_types=parse_result["return_types"] if line_match=="function" else None
                    body,rest=get_to_matching_brace(code_block)
                    code_block=rest
                    out.append(process(parsers,line_match,body,namespace,ret_types))
                    match=1
                    break

        if match==0:
           
            out.append(window[0])
            code_block="\n".join(code_block.splitlines()[1:])

    return "\n".join(out)
    
#------------------------------------------------------------------------------------------------------------
def sub_line_numbers(l):
    
    ll=l.splitlines()
    for i in range(0,len(ll)):
        ll[i]=re_line.sub(str(i+1),ll[i])
       
    return "\n".join(ll)
    
#------------------------------------------------------------------------------------------------------------
  
def main():
    
    global debugmode 
    optparse = OptionParser()
    optparse.add_option("-d", "--debug", action="store_true", dest="debug", default=False)
    (options, args) = optparse.parse_args()
    debugmode=options.debug    
    
    parsers={ 
              "function"   : function,
              "procedure"  : procedure,
              "select"     : select,
              "update"     : update,
              "class"      : class_,
              "return"     : return_
            }
    
    for f in args:
        
        textfile=open(f,"r")
        text=textfile.read()
        namespace=f.split(".")[0]
        res=process( parsers,"toplevel", text , namespace, None)
        res=sub_line_numbers(res)
        
        with open("parse.out","w") as outf:
            print >>outf,res 
        print res 
        
if __name__=="__main__":
    main()

