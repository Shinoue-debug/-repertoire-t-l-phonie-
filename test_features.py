import sqlite3
import unittest

from app import initialiser_bdd, importer_contacts_depuis_rows, normaliser_tags


class FeaturesContactsTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        initialiser_bdd(self.conn)

    def test_normaliser_tags(self):
        self.assertEqual(normaliser_tags(' Ami, famille,  travail '), ['Ami', 'famille', 'travail'])
        self.assertEqual(normaliser_tags(''), [])

    def test_importer_contacts_depuis_rows_cree_contacts_et_tags(self):
        rows = [
            {
                'nom': 'Durand',
                'prenom': 'Claire',
                'telephone': '0123456789',
                'email': 'claire@example.com',
                'notes': 'Client VIP',
                'tags': 'famille,pro',
            }
        ]

        contacts_importes = importer_contacts_depuis_rows(self.conn, rows)

        self.assertEqual(len(contacts_importes), 1)
        contact = self.conn.execute('SELECT * FROM contacts WHERE nom = ?', ('Durand',)).fetchone()
        self.assertIsNotNone(contact)
        tags = self.conn.execute(
            '''
            SELECT t.nom
            FROM tags t
            JOIN contact_tags ct ON ct.tag_id = t.id
            WHERE ct.contact_id = ?
            ORDER BY t.nom
            ''',
            (contact['id'],),
        ).fetchall()
        self.assertEqual([tag['nom'] for tag in tags], ['famille', 'pro'])


if __name__ == '__main__':
    unittest.main()
