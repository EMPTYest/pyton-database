import psycopg2
import time

class Model:

    def __init__(self):
        self.conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='1111',
            host='localhost',
            port=5432
        )

    def get_all_tables(self):
        c = self.conn.cursor()
        c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        return c.fetchall()

    def add_data(self, table_name, columns, val):
        c = self.conn.cursor()

        columns_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(val))

        identifier_column = f'{table_name.lower()}_id'
        c.execute(f'SELECT {identifier_column} FROM "public"."{table_name}"')
        existing_identifiers = {row[0] for row in c.fetchall()}

        try:
            identifier_index = columns.index(identifier_column)
            val[identifier_index] = int(val[identifier_index])
        except ValueError:
            raise ValueError(f"Column {identifier_column} not found in columns: {columns}")

        external_keys = [col for col in columns if col.endswith('_id') and col != identifier_column]

        if val[identifier_index] in existing_identifiers:
            return 2

        for key_column in external_keys:
            referenced_table = key_column[:-3].capitalize()
            c.execute(f'SELECT {key_column} FROM "public"."{referenced_table}"')
            referenced_values = {row[0] for row in c.fetchall()}

            val_index = columns.index(key_column)
            val_id = int(val[val_index])

            if val_id not in referenced_values:
                return 3

        # Insert the data
        try:


            c.execute(f'INSERT INTO "public"."{table_name}" ({columns_str}) VALUES ({placeholders})', val)
            self.conn.commit()
            return 1
        except Exception as e:

            return 4



    def update_data(self, table_name, column, record_id, new_value):
            c = self.conn.cursor()
            identifier_column = f'{table_name.lower()}_id'


            # Check  unique identifier
            if column == identifier_column:

                c.execute(f'SELECT {identifier_column} FROM "public"."{table_name}"')
                existing_identifiers = {row[0] for row in c.fetchall()}

                new_value = int(new_value)


                if new_value in existing_identifiers:
                    return 2
            # Check if the column being updated is a foreign key
            elif column.endswith('_id'):
                referenced_table = column[:-3].capitalize()


                c.execute(f'SELECT {column} FROM "public"."{referenced_table}"')
                valid_values = {row[0] for row in c.fetchall()}


                new_value = int(new_value)

                # Ensure the new foreign key value exists in the referenced table
                if new_value not in valid_values:
                    return 3

            # Update the record in the table
            c.execute(
                f'UPDATE "public"."{table_name}" SET {column} = %s WHERE {identifier_column} = %s',
                (new_value, record_id)
            )
            self.conn.commit()
            return 1  # Successfully updated



    def delete_data(self, table_name, record_id):
        c = self.conn.cursor()

        try:

            c.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in c.fetchall()]

            # Check for references in other tables
            for current_table in tables:
                if current_table == table_name:
                    continue

                c.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (current_table,))
                column_names = [row[0] for row in c.fetchall()]


                foreign_key_column = f'{table_name.lower()}_id'
                if foreign_key_column in column_names:
                    # Check if ID is referenced
                    c.execute(f'SELECT {foreign_key_column} FROM "public"."{current_table}"')
                    referenced_values = {row[0] for row in c.fetchall()}

                    if record_id in referenced_values:
                        return 0  # Cannot delete because the record is referenced

            # Delete the record from the target table

            c.execute(f'DELETE FROM "public"."{table_name}" WHERE {table_name.lower()}_id = %s', (record_id,))
            self.conn.commit()
            return 1  # Successfully deleted

        except Exception as e:
            return 4

    def generate_data(self, table_name, count):

        c = self.conn.cursor()
        try:
            c.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", (table_name,))
            columns_info = c.fetchall()


            id_column = f'{table_name.lower()}_id'
            name=''

            for i in range(count):
                insert_query = f'INSERT INTO "public"."{table_name}" ('
                select_subquery = ""

                for column_info in columns_info:
                    column_name = column_info[0]
                    column_type = column_info[1]

                    if column_name == id_column:
                        c.execute(f'SELECT max("{id_column}") FROM "public"."{table_name}"')
                        max_id = c.fetchone()[0] or 0
                        select_subquery += f'{max_id + 1},'
                    elif column_name == "name":
                        c.execute(f"SELECT CASE FLOOR(1 + RANDOM() * 5)::INT  WHEN 1 THEN 'Olexandr' WHEN 2 THEN 'Maria' WHEN 3 THEN 'Ivan' WHEN 4 THEN 'Anna' WHEN 5 THEN 'Dmitro' END ")
                        name = c.fetchone()[0]
                        select_subquery += f"'{name}',"
                    elif column_name == "email":
                        select_subquery += f"'{name}@example.com',"
                    elif column_name.endswith('_id'):
                        related_table_name = column_name[:-3].capitalize()
                        c.execute(f'SELECT {related_table_name.lower()}_id FROM "public"."{related_table_name}" ORDER '
                                  f'BY RANDOM() LIMIT 1')
                        related_id = c.fetchone()[0]

                        select_subquery += f'{related_id},'
                    elif column_type == 'integer':
                        select_subquery += f'trunc(random()*100)::INT,'
                    elif column_type == 'character varying':
                        c.execute(
                            f"SELECT CASE FLOOR(1 + RANDOM() * 2)::INT  WHEN 1 THEN 'some text' WHEN 2 THEN 'not some text'  END ")
                        name1 = c.fetchone()[0]
                        select_subquery += f"'{name1}',"
                    elif column_type == 'timestamp with time zone':
                        c.execute(f"SELECT timestamp with time zone '2022-01-01 08:30:00+03' + random() * (timestamp with time zone '2022-10-01 08:30:00+03' - timestamp with time zone '2022-01-01 20:30:00+03')")
                        name = c.fetchone()[0]
                        select_subquery += f"'{name}',"
                    else:
                        continue

                    insert_query += f'"{column_name}",'

                insert_query = insert_query.rstrip(',') + f') VALUES ({select_subquery[:-1]})'

                c.execute(insert_query)

            self.conn.commit()
            return 1
        except Exception as e:
            return 2

    def search_data(self, table, stable, row_name, row_data, group_name):
            c = self.conn.cursor()
            start = time.time()


            c.execute(f'SELECT   u.{group_name} AS {group_name}, COUNT(o.{stable.lower()}_id) AS totalarticles    FROM public."{table}" u  JOIN  public."{stable}" o ON u.{table.lower()}_id = o.{table.lower()}_id WHERE  u.{row_name}='f"'{row_data}' GROUP BY  u.{group_name} ORDER BY totalarticles DESC;")
            r = c.fetchall()

            print(f"|{group_name}|Всього збігів|")
            for s in r:
                print(s)
            end = time.time() - start
            print(f"Витрачено часу: {end*1000} ms")
            return 1


    def print_table(self, table):
            c = self.conn.cursor()

            c.execute(f'SELECT * FROM "public"."{table}"' f"Order BY {table.lower()}_id")
            r = c.fetchall()
            for s in r:
                print(s)
            return 1
