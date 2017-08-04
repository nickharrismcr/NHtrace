#! /usr/bin/env python
'''
Created on 27 Jul 2017

@author: nick

Add debug trace to a new horizon .v sourcefile with line number, full namespace and call/return parameters
can also include global variable values on routine entry/exit 

NB the process can add newlines to the source in various places. don't check traced code into VC. 

usage : NHtrace.py [--global var[,var]...][--restore][--debug][--test] sourcefile [ sourcefile ]...

--global  : comma separated list of global variables to trace
--restore : restore backup of source  
--debug   : output debugging info
--test    : run unit tests 

e.g NHtrace.py --global gl_client_no,gl_mail_no request.v promotions.v 

Uses pyparsing library 
http://pyparsing.wikispaces.com

TODO : integrity modules 

'''
#------------------------------------------------------------------------------------------------------------     
import sys, re, pyparsing as pp, datetime, os, shutil, unittest, subprocess
import NHtrace_tests 
from optparse import OptionParser 
#------------------------------------------------------------------------------------------------------------     

# modify this to whatever your trace output routine is, must be of the format call <proc>(("%s",%s))
# and the routine must take a single string parameter. 

tracecall='call debug.DebugNL(("%s",%s))'

printables={
            "small number":True,
            "large number":True,
            "number":True,
            "string":True,
            "boolean":True,
            "date":True,
            "time":True,
            "money":True,
            "text":True
           }

debugmode=False 

#------------------------------------------------------------------------------------------------------------     
# regexp defs
#------------------------------------------------------------------------------------------------------------     

re_class=re.compile("(public class|class)")
re_select=re.compile("[ \t]select[ \t]")
re_update=re.compile("[ \t]update[ \t]")
re_comment=re.compile("--.*")
re_return=re.compile("^[ \t]*return[ \t$\(]")
re_line=re.compile("@line@")
re_remove_list=re.compile("[\[\]']")
re_notallowed=re.compile("[\[\]\(\)->+*-\/]")

#------------------------------------------------------------------------------------------------------------     
# pyparsing grammar definition 
#------------------------------------------------------------------------------------------------------------     

# result names are attached to the parsers matching the function/procedure/class names and sql tablenames.
# e.g  classname=pp.Word(pp.alphanums+"_").setResultsName("class") 
# the returned string from the check() function will be one of these names, this (a) selects the 
# parser object to use from the parsers dictionary and (b) provides the key when accessing the parse result
# object to pull out the name. 

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
STRING=pp.Keyword("string")+pp.Optional("length"+pp.Word(pp.nums))
BOOLEAN=pp.Keyword("boolean")
FIXED=pp.Keyword("fixed")
POINT=pp.Keyword("point")
PREC=pp.Keyword("prec")
FIXEDPOINTPREC=FIXED+POINT+PREC+pp.Word(pp.nums)
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
dblDashComment = pp.Regex(r"--(?:\\\n|[^\n])*").setName("-- comment")

#variable/label name
name=pp.Word(pp.alphanums+"_"+".")

#sql 
astuple=AS+name 
select_tablename=(pp.Optional(name+EQ).suppress()+name ).setResultsName("select")
update_tablename=(pp.Optional(name+EQ).suppress()+name ).setResultsName("update")
tablefield=pp.Word(pp.alphanums+"_"+".")
tablefields=pp.Optional(tablefield ^ pp.delimitedList(tablefield,","))

#class   
pptype=pp.Word(pp.alphanums+"."+"_")
classname=pp.Word(pp.alphanums+"_").setResultsName("class") 

# function/proc name 
funcname=pp.Word(pp.alphanums+"_").setResultsName("function")
procname=pp.Word(pp.alphanums+"_").setResultsName("procedure")

# parameter compounds 
types=(NUMBER ^ LARGENUMBER ^ SMALLNUMBER ^ STRING ^ TEXT ^ DATE ^ BOOLEAN ^ FIXEDPOINTPREC ^ pptype)
DEFARRAY=ARRAY+OF+types
paramtype=pp.Group( (types ^ DEFARRAY) + pp.Optional(WITHNULL))
param= (name + IS + paramtype) 
param_list=pp.Group( OPB + pp.Optional(pp.delimitedList(param, ",")) + CLB).setResultsName("parameter_list") 
param_list.ignore(dblDashComment)

# return compounds 
single_ret=paramtype
multi_ret=OPB + pp.delimitedList(paramtype,",") + CLB
returntypes=pp.Group(multi_ret ^ single_ret).setResultsName("return_types")
returnvalues=pp.SkipTo("}",include=True).setResultsName("return_values") 

simple_return=(name|(pp.delimitedList(name)))


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
[ f.ignore(dblDashComment) for f in [ function, procedure, return_, select, update, class_ ]]



##------------------------------------------------------------------------------------------------------------  
def debug(txt):
    if debugmode:

        print txt      

#------------------------------------------------------------------------------------------------------------     
def get_parameter_value_strings(param_list,globals_,p1,p2):
    
    param_count=len(param_list)/2

    if param_count==0:
	p1+="[<>]"
        p2+='""'
        return p1,p2 

    for i in range(0,param_count):
        param_name=param_list[i*2]
        param_type=param_list[i*2+1]
        p1+="[<>]" 
        # only attempt to trace basic types. dont trace if "with null" 
        if len(param_type)==1 and param_type[0] in printables:
            p2+=param_name+","  
        else:
            p2+='"_",'
    
     
    for g in globals_:
        p1+=" %s [<>]" % g
        p2+=g+","
    
    # bin last comma    
    if len(p2)>0 and p2[-1]==",":
        p2=p2[:-1]
        
    return p1,p2

#------------------------------------------------------------------------------------------------------------     
def get_return_value_string(param_list, return_types, globals_, p1,p2 ):

    # return values. only trace them if we have a simple value or tuple of values.
    # no expressions or function calls allowed, avoids side effects or compilation issues 
    
    p1+="<>"
    p2+='"",'

    if re_notallowed.search(param_list)==None:

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
		    p2+='"_",'
	    
	    for g in globals_:
		p1+=" %s [<>]" % g
		p2+=g+","
	    
		     
	except:
	    # match failed
	    pass
    
    # bin the last comma
    if len(p2)>0 and p2[-1]==",":
        p2=p2[:-1]

    return p1,p2 
#------------------------------------------------------------------------------------------------------------     
def get_return_string(globals_, p1,p2 ):
    
    p1+="<>"
    p2+='"",' 

    for g in globals_:
        p1+=" %s [<>]" % g
        p2+=g+","
    
    # bin the last comma
    if len(p2)>0 and p2[-1]==",":
        p2=p2[:-1]

    return p1,p2 

#------------------------------------------------------------------------------------------------------------     
def def_trace(which, name, param_list, return_types, globals_ ):
    
    # returns 4gl trace call statement to add to the .v 
    # @line@ numbers will be substituted once we've finished the main processing
    # easier that way with all the recursion going on....
    
    module=name.split(".")[0]+".v"
    where=".".join(name.split(".")[1:]) 
    
    strings={
             "procedure" : "%s : %s : p %s " % (module,"@line@",where),
             "function"  : "%s : %s : f %s " % (module,"@line@",where),
             "select"    : "%s : %s : %s %s " % (module,"@line@",where,which),
             "update"    : "%s : %s : %s %s " % (module,"@line@",where,which),
             "return"    : "%s : %s : ret %s " % (module,"@line@",where),
             }
    
    if not which in strings:
        return ""
    
    p1=strings[which]
    p2=""
    
    if which in ("function","procedure"):
        
        p1,p2=get_parameter_value_strings(param_list,globals_,p1,p2)
              
    elif which=="return":
        
        if return_types != None:
            p1,p2=get_return_value_string(param_list, return_types, globals_, p1,p2 )
        else:
            p1,p2=get_return_string(globals_,p1,p2)
            
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
    comment=0
    while True:
	if code_block[en-2:en]=="--":
            comment=1
	if code_block[en]=="\n":
            comment=0

	if comment==0:
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
    
    if check_func(line):
        return "function"
    elif check_proc(line):
        return "procedure"
    elif re_return.search(line0):
        return "return"
    elif re_select.search(line0):
        return "select" 
    elif re_update.search(line0):
        return "update"
    elif re_class.search(line):
        return "class"
    
    return None 
#------------------------------------------------------------------------------------------------------------     
def process(parsers,parent,code_block,parent_name,globals_,parent_ret_types):
    
    '''  
    check a three line lookahead from the current line for class|function|procedure defs 
    or the current line for return|select|update statements
    for speed, function and procedure checks use a small parser, rest use regexps 
    if match found, run it through the relevant full parser to pull out the required items so we can insert
    a trace line to the outputted code 
    
    this will be recursively called when handling nested statement bodies 
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
                        debug("parsed "+line_match+"\n"+str(window)+"\n"+matched)
                        ret_values=parse_result["return_values"] 
                        # add trace line 
                        out.append(def_trace(line_match,parent_name,ret_values,parent_ret_types,globals_))         
                        out.append(code_block[0:start]+matched)     #keeps indent 
                        code_block=code_block[end:]
                        namespace=parent_name
                        match=1
                        break
                    
                elif parent=="procedure":
                    
                    # add trace line 
                    out.append(def_trace(line_match,parent_name,None,None,globals_))         
                    
            else:
                 
                for parse_result,start,end in parsers[line_match].scanString(code_block):
                    
                    matched=code_block[start:end]            
                    debug("parsed "+line_match+"\n"+str(window)+"\n"+matched+"|")
                    out.append(code_block[0:start]+matched)     #keeps indent 
                    code_block=code_block[end:]
                    dot="->" if parent=="class" else "."
                    namespace=parent_name+dot+mystr(parse_result[line_match])
                    params=parse_result["parameter_list"] if line_match in ("procedure","function") else None
                    # add trace line 
                    out.append(def_trace(line_match,namespace,params,None,globals_))
                    ret_types=parse_result["return_types"] if line_match=="function" else None
                    body,rest=get_to_matching_brace(code_block)
                    code_block=rest
                    # recursive call handles nested block 
                    out.append( process(parsers,line_match,body,namespace,globals_,ret_types) )
                    match=1
                    break

        if match==0:
           
            out.append(window[0])
            code_block="\n".join(code_block.splitlines()[1:])

    return "\n".join(out)
    
#------------------------------------------------------------------------------------------------------------
def sub_line_numbers(l):
    
    # replace @line@ placeholders with actual source linenumbers 
    
    ll=l.splitlines()
    for i in range(0,len(ll)):
        ll[i]=re_line.sub(str(i+1),ll[i])
       
    return "\n".join(ll)
 
#------------------------------------------------------------------------------------------------------------
def restore_saved(filename):
    
    datestamp=datetime.datetime.now().strftime("%Y%m%d")
    backup=filename+".orig."+datestamp
    shutil.move(backup,filename)
    print "restored %s to %s " % (backup,filename)

#------------------------------------------------------------------------------------------------------------
def backup_source(filename):     
    
    datestamp=datetime.datetime.now().strftime("%Y%m%d")
    backup=filename+".orig."+datestamp
    shutil.copyfile(filename,backup)
    return backup


#------------------------------------------------------------------------------------------------------------
def get_globals_to_watch(list_):
    
    if list_ is None:
        return []
    if "," in list_:
        return list_.split(",")
    else:
        return [ list_ ]
    
#------------------------------------------------------------------------------------------------------------
class Test(unittest.TestCase):
    
    def test_strings(self):
        
        def diff(a,b):
            import difflib
            return "\n".join([ i for i in difflib.context_diff(a.splitlines(),b.splitlines())])
        
        parsers={ 
              "function"   : function,
              "procedure"  : procedure,
              "select"     : select,
              "update"     : update,
              "class"      : class_,
              "return"     : return_
            }
    
        for s in NHtrace_tests.__dict__.keys():
            if s[0:2]!="__" and s[0:3]!="out":
                print >>sys.stderr, (s)
                res=process( parsers,"toplevel", NHtrace_tests.__dict__[s] , s , [], None)
                res=sub_line_numbers(res)
                expected=NHtrace_tests.__dict__["out_"+s]
                d=diff(res,expected)
                assert len(d)==0, "%s fail : \n%s " % (s,d)
                
#------------------------------------------------------------------------------------------------------------ 
def vgen(g_module):

    ''' attempt to compile the traced module and return success/failure  ''' 

    home=os.getenv("HOME","")
    if home != "":
        cwd=os.getcwd()
	base=os.path.basename(g_module)
	tmp=os.path.join(home,base)
	shutil.copyfile(g_module,tmp)
        os.chdir(home)
	try:
	    check_output("vgen -d sunres %s" % g_module)
	    vmc=os.path.basename(g_module).split(".")[0]+".vmc"
	    os.remove(vmc)
	    os.remove(tmp)
	    os.chdir(cwd)    
	except StandardError,e:
	    print str(e)+"\n"
	    print "Compile failed for %s " % g_module
	    os.remove(tmp)
	    os.chdir(cwd)    
	    return False

    return True

#--------------------------------------------------------------------------------------------------------------------           
# from Python 2.7 subprocess.check_output 

def check_output(*popenargs, **kwargs):

    STDOUT = subprocess.STDOUT
    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, *popenargs, **kwargs)
    output, err  = process.communicate()
    retcode = process.poll()
    if retcode:
	raise StandardError(err)
    return output

#--------------------------------------------------------------------------------------------------------------------           
#------------------------------------------------------------------------------------------------------------------------------        
#------------------------------------------------------------------------------------------------------------------------------        

def main():
    
    global debugmode 
    optparse = OptionParser()
    optparse.add_option("-d", "--debug", action="store_true", dest="debug", default=False)
    optparse.add_option("-r", "--restore", action="store_true", dest="restore", default=False)
    optparse.add_option("-g", "--global", dest="globalnames", default=None )
    optparse.add_option("-t", "--test", action="store_true", dest="test", default=False)
    (options, args) = optparse.parse_args()
    debugmode=options.debug
    globals_=get_globals_to_watch(options.globalnames)
    
    parsers={ 
              "function"   : function,
              "procedure"  : procedure,
              "select"     : select,
              "update"     : update,
              "class"      : class_,
              "return"     : return_
            }
    
    if options.test:
        #unittest.main(argv=sys.argv[:1])
	res=process(parsers,"module",NHtrace_tests.adhoc,"test",[],None) 
	print "test:",res 
    else:
        for f in args:
            
            if options.restore:
                restore_saved(f)
            else:
		print "Adding trace to %s" % f 
                backup=backup_source(f)
                text=open(f,"r").read()
                namespace=f.split(".")[0]
                res=process( parsers,"module", text , namespace, globals_, None)
                res=sub_line_numbers(res)
                with open(f+".out","w") as outf:
                    print >>outf,res 
                shutil.move(f+".out",f)
		if vgen(f):
			print "Trace added to %s : backup is %s " % (f, backup)
		
                
#------------------------------------------------------------------------------------------------------------------------------        
#------------------------------------------------------------------------------------------------------------------------------        
#------------------------------------------------------------------------------------------------------------------------------        

if __name__=="__main__":
  
    main()

