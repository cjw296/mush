from .example_without_mush import main
from unittest import TestCase
from testfixtures import TempDirectory, Replacer
import sqlite3

class Tests(TestCase):

    def test_main(self):
        with TempDirectory() as d:
            # setup db
            db_path = d.getpath('sqlite.db')
            conn = sqlite3.connect(db_path)
            conn.execute('create table notes (filename varchar, text varchar)')
            conn.commit()
            # setup config
            config = d.write('config.ini', '''
[main]
db = %s
log = %s
''' % (db_path, d.getpath('script.log')))
            # setup file to read
            source = d.write('test.txt', 'some text')
            with Replacer() as r:
                r.replace('sys.argv', ['script.py', config, source, '--quiet'])
                main()
            # check results
            self.assertEqual(
                conn.execute('select * from notes').fetchall(),
                [('test.txt', 'some text')]
                )

    def test_main_verbose(self):
        with TempDirectory() as d:
            # setup db
            db_path = d.getpath('sqlite.db')
            conn = sqlite3.connect(db_path)
            conn.execute('create table notes (filename varchar, text varchar)')
            conn.commit()
            # setup config
            config = d.write('config.ini', '''
[main]
db = %s
log = %s
''' % (db_path, d.getpath('script.log')))
            # setup file to read
            source = d.write('test.txt', 'some text')
            with Replacer() as r:
                r.replace('sys.argv', ['script.py', config, source])
                main()

    def test_main_exception(self):
        with TempDirectory() as d:
            from testfixtures import OutputCapture
            # setup db
            db_path = d.getpath('sqlite.db')
            conn = sqlite3.connect(db_path)
            # don't create the table so we get at exception
            conn.commit()
            # setup config
            config = d.write('config.ini', '''
[main]
db = %s
log = %s
''' % (db_path, d.getpath('script.log')))
            # setup file to read
            source = d.write('bad.txt', 'some text')
            with Replacer() as r:
                r.replace('sys.argv', ['script.py', config, source])
                with OutputCapture() as output:
                    main()
            self.assertTrue('OperationalError' in output.captured,
                            output.captured)
