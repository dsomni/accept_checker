import json
from manager import run
import os


'''
NOTES

It's ok that TEST SET#1 raises error for cpp,
because cpp compiler do not stop program after
throwing a ZeroDevision exception

'''

tests0 = [
    ["1", "1"],
    ["0", "1"],
    ["10", "11"],
]
pythonCode0 = "i = int(input())\nprint(i+1)"
cppCode0 = '#include <iostream>\n using namespace std;\nint main()\n{\nint a; cin >> a; cout << a+1;\nreturn 0;\n}'
javaCode0 = 'import java.util.Scanner;\nclass Main\n{ public static void main(String args[])\n{ Scanner in = new Scanner(System.in);\nint num = in.nextInt();\nSystem.out.println(num+1); } }\nclass Simple\n{ public void run(String args[]) { } }'
pascalCode0 = 'var i:integer; Begin readln(i); writeln(i+1); End.'


tests1 = [
    ["0", "1"],
]
pythonCode1 = "i = int(input())\nprint(1/i)"
cppCode1 = '#include <iostream>\n using namespace std;\nint main()\n{\nint a; cin >> a; cout << 1/a;\nreturn 0;\n}'
javaCode1 = 'import java.util.Scanner;\nclass Main\n{ public static void main(String args[])\n{ Scanner in = new Scanner(System.in);\nint num = in.nextInt();\nSystem.out.println(1/num); } }\nclass Simple\n{ public void run(String args[]) { } }'
pascalCode1 = 'var i:integer; Begin readln(i); writeln(1 div i); End.'

tests2 = [
    ["0", "1"],
    ["1", "1"],
]
pythonCode2 = "i = int(input())\nwhile(i==1):\n\ta=1\nprint(1)"
cppCode2 = '#include <iostream>\n using namespace std;\nint main()\n{\nint a; cin >> a;while(a==1){int b = 1;}; cout << 1;\nreturn 0;\n}'
javaCode2 = 'import java.util.Scanner;\nclass Main\n{ public static void main(String args[])\n{ Scanner in = new Scanner(System.in);\nint num = in.nextInt();while(num==1){int b = 1;};\nSystem.out.println(1); } }\nclass Simple\n{ public void run(String args[]) { } }'
pascalCode2 = 'var i,b:integer; Begin readln(i); while(i=1) do b := 1; writeln(1); End.'

checker_tests = [
    [{'pascal': pascalCode0, 'python': pythonCode0, 'pypy': pythonCode0, 'cpp': cppCode0, 'java': javaCode0},
     tests0,
     ['Test#1 WA Wrong Answer', 'Test#2 OK OK', 'Test#3 OK OK']],

    [{'pascal': pascalCode1, 'python': pythonCode1, 'pypy': pythonCode1, 'cpp': cppCode1, 'java': javaCode1},
     tests1,
     ['Test#1 RE Runtime Error']],

    [{'pascal': pascalCode2, 'python': pythonCode2, 'pypy': pythonCode2, 'cpp': cppCode2, 'java': javaCode2},
     tests2,
     ['Test#1 OK OK', 'Test#2 TL Time Limit']],
]

langs_configs = []
with open(os.path.abspath(os.path.join('.', 'langs.json')), "r") as file:
    langs_configs = json.load(file)
langs = list(langs_configs.keys())


def test(start_with=0):
    for i in range(start_with,len(checker_tests)):
        print(f'\nTEST SET #{i}')
        codes, test_set, answer = checker_tests[i]
        for lang in langs:
            text = codes[lang]
            results = run(lang, text, test_set, should_print_command=False, should_before_end=True)
            print(lang, end=' ')
            if(results == answer):
                print('OK')
            else:
                print('ERROR')
                print(results)
                print(answer)
                print()


test()
