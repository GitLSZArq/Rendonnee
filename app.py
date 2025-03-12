import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import psycopg2

st.set_page_config(layout="wide")

# ------------------------------------------------------------------
# GESTION DE LA BASE DE DONNÉES
# ------------------------------------------------------------------

def get_connection():
    # Récupère l'URL de connexion stockée dans st.secrets
    db_url = st.secrets["db_url"]
    conn = psycopg2.connect(db_url)
    return conn

def init_db(conn):
    """Crée les tables nécessaires si elles n'existent pas déjà."""
    c = conn.cursor()
    # Table des types de cartouches
    c.execute('''
        CREATE TABLE IF NOT EXISTS cartridge_types (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            full_gas_mass REAL NOT NULL,
            empty_mass REAL NOT NULL,
            color TEXT NOT NULL,
            butane REAL NOT NULL,
            propane REAL NOT NULL
        )
    ''')
    # Table pour l'historique des transactions, avec nom du client
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            cartridge_type_id INTEGER NOT NULL,
            color TEXT NOT NULL,
            measured_weight REAL NOT NULL,
            gas_mass REAL NOT NULL,
            missing_gas REAL NOT NULL,
            butane_to_add REAL NOT NULL,
            propane_to_add REAL NOT NULL,
            client_name TEXT,
            FOREIGN KEY(cartridge_type_id) REFERENCES cartridge_types(id)
        )
    ''')
    conn.commit()

def add_default_cartridge_types(conn):
    """Ajoute 5 types de cartouches par défaut s'ils n'existent pas déjà."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cartridge_types")
    count = c.fetchone()[0]
    if count == 0:
        default_types = [
            ("Type A", 400.0, 200.0, "Bleu", 0.70, 0.30),
            ("Type B", 500.0, 250.0, "Rouge", 0.60, 0.40),
            ("Type C", 450.0, 220.0, "Bleu", 0.70, 0.30),
            ("Type D", 600.0, 300.0, "Rouge", 0.60, 0.40),
            ("Type E", 550.0, 280.0, "Bleu", 0.70, 0.30)
        ]
        c.executemany('''
            INSERT INTO cartridge_types 
            (name, full_gas_mass, empty_mass, color, butane, propane) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', default_types)
        conn.commit()

def get_cartridge_types(conn):
    """Retourne tous les types de cartouches sous forme de DataFrame."""
    c = conn.cursor()
    c.execute("SELECT * FROM cartridge_types")
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=['id', 'name', 'full_gas_mass', 'empty_mass', 'color', 'butane', 'propane'])
    return df

def add_cartridge_type(conn, name, full_gas_mass, empty_mass, color, butane, propane):
    """Ajoute un nouveau type de cartouche."""
    c = conn.cursor()
    c.execute('''
        INSERT INTO cartridge_types 
        (name, full_gas_mass, empty_mass, color, butane, propane) 
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (name, full_gas_mass, empty_mass, color, butane, propane))
    conn.commit()

def update_cartridge_type(conn, id, name, full_gas_mass, empty_mass, color, butane, propane):
    """Met à jour un type de cartouche existant."""
    c = conn.cursor()
    c.execute('''
        UPDATE cartridge_types 
        SET name=%s, full_gas_mass=%s, empty_mass=%s, color=%s, butane=%s, propane=%s 
        WHERE id=%s
    ''', (name, full_gas_mass, empty_mass, color, butane, propane, id))
    conn.commit()

def delete_cartridge_type(conn, type_id):
    c = conn.cursor()
    c.execute("DELETE FROM cartridge_types WHERE id=%s", (type_id,))
    conn.commit()


def add_transaction(conn, cartridge_type_id, color, measured_weight, gas_mass, missing_gas, butane_to_add, propane_to_add, client_name):
    """Ajoute une transaction dans la base."""
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO transactions 
        (date, cartridge_type_id, color, measured_weight, gas_mass, missing_gas, butane_to_add, propane_to_add, client_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (date_str, cartridge_type_id, color, measured_weight, gas_mass, missing_gas, butane_to_add, propane_to_add, client_name))
    conn.commit()

def get_transactions(conn):
    """Retourne toutes les transactions sous forme de DataFrame."""
    c = conn.cursor()
    c.execute('''
        SELECT t.id, t.date, ct.name as cartridge_name, t.color, t.measured_weight, 
               t.gas_mass, t.missing_gas, t.butane_to_add, t.propane_to_add, t.client_name
        FROM transactions t
        JOIN cartridge_types ct ON t.cartridge_type_id = ct.id
        ORDER BY t.date DESC
    ''')
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=[
        'ID', 'Date', 'Type de cartouche', 'Couleur', 
        'Poids mesuré (g)', 'Masse de gaz (g)', 'Gaz manquant (g)', 
        'Butane à ajouter (g)', 'Propane à ajouter (g)', 'Nom du client'
    ])
    return df

def delete_transaction(conn, transaction_id):
    """Supprime une transaction par son ID."""
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=%s", (transaction_id,))
    conn.commit()

def update_transaction(conn, transaction_id, new_date, new_measured_weight, 
                       new_gas_mass, new_missing_gas, new_butane_to_add, 
                       new_propane_to_add, new_client_name):
    """Met à jour une transaction existante."""
    c = conn.cursor()
    c.execute('''
        UPDATE transactions
        SET date=%s, measured_weight=%s, gas_mass=%s, missing_gas=%s, 
            butane_to_add=%s, propane_to_add=%s, client_name=%s
        WHERE id=%s
    ''', (new_date, new_measured_weight, new_gas_mass, new_missing_gas, 
          new_butane_to_add, new_propane_to_add, new_client_name, transaction_id))
    conn.commit()

# ------------------------------------------------------------------
# INTERFACE STREAMLIT
# ------------------------------------------------------------------

def main():
    st.title("Application de Remplissage des Cartouches")

    # Connexion et initialisation DB
    conn = get_connection()
    init_db(conn)
    add_default_cartridge_types(conn)
    
    # Menu
    menu = st.sidebar.selectbox("Menu", ["Transaction", "Configuration", "Historique"])
    
    if menu == "Transaction":
        st.header("Nouvelle Transaction")
        df_types = get_cartridge_types(conn)
        if df_types.empty:
            st.error("Aucun type de cartouche disponible. Veuillez ajouter un type dans la section Configuration.")
        else:
            # Sélection du type
            type_options = df_types['name'].tolist()
            selected_type_name = st.selectbox("Sélectionnez le type de cartouche", type_options)
            selected_type = df_types[df_types['name'] == selected_type_name].iloc[0]
            
            st.write(f"Type choisi: **{selected_type['name']}** (Couleur: {selected_type['color']})")
            
            # Nom du client
            client_name = st.text_input("Nom du client (optionnel)", value="")
            
            # Poids mesuré
            measured_weight = st.number_input("Entrez le poids mesuré de la cartouche (en grammes)", 
                                              min_value=0.0, format="%.2f")
            
            # Un seul bouton pour calculer ET enregistrer
            if st.button("Calculer et Enregistrer"):
                empty_mass = selected_type['empty_mass']
                full_gas_mass = selected_type['full_gas_mass']
                gas_mass = measured_weight - empty_mass
                if gas_mass < 0:
                    st.error("Le poids mesuré est inférieur à la masse du contenant vide.")
                else:
                    missing_gas = full_gas_mass - gas_mass
                    missing_gas = missing_gas if missing_gas > 0 else 0
                    
                    butane_percentage = selected_type['butane']
                    propane_percentage = selected_type['propane']
                    
                    butane_to_add = missing_gas * butane_percentage
                    propane_to_add = missing_gas * propane_percentage
                    
                    # Afficher les résultats
                    st.subheader("Résultats")
                    st.write(f"Masse de gaz actuel : **{gas_mass:.2f} g**")
                    st.write(f"Gaz manquant pour remplir : **{missing_gas:.2f} g**")
                    st.write(f"Pour une cartouche {selected_type['color']} :")
                    st.write(f" - Butane ({butane_percentage*100:.0f}%): **{butane_to_add:.2f} g**")
                    st.write(f" - Propane ({propane_percentage*100:.0f}%): **{propane_to_add:.2f} g**")
                    
                    # Enregistrer directement
                    add_transaction(
                        conn=conn,
                        cartridge_type_id=int(selected_type['id']),
                        color=selected_type['color'],
                        measured_weight=measured_weight,
                        gas_mass=gas_mass,
                        missing_gas=missing_gas,
                        butane_to_add=butane_to_add,
                        propane_to_add=propane_to_add,
                        client_name=client_name
                    )
                    st.success("Transaction enregistrée avec succès!")
    
    elif menu == "Configuration":
        st.header("Configuration des Types de Cartouches")
        
        # Afficher les types existants
        st.subheader("Liste des Types Existants")
        df_types = get_cartridge_types(conn)
        st.dataframe(df_types)
        
        # Formulaire d'ajout
        st.subheader("Ajouter un nouveau type de cartouche")
        with st.form("ajout_type"):
            new_name = st.text_input("Nom du type de cartouche")
            new_full_gas_mass = st.number_input("Masse de gaz pleine (g)", min_value=0.0, format="%.2f")
            new_empty_mass = st.number_input("Masse du contenant vide (g)", min_value=0.0, format="%.2f")
            new_color = st.selectbox("Sélectionnez la couleur", ["Bleu", "Rouge"])
            # Valeurs par défaut
            if new_color == "Bleu":
                default_butane = 0.70
                default_propane = 0.30
            else:
                default_butane = 0.60
                default_propane = 0.40
            
            new_butane = st.number_input("Pourcentage de Butane (ex: 0.70 pour 70%)", 
                                         min_value=0.0, max_value=1.0, value=default_butane, format="%.2f")
            new_propane = st.number_input("Pourcentage de Propane (ex: 0.30 pour 30%)", 
                                          min_value=0.0, max_value=1.0, value=default_propane, format="%.2f")
            
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                if new_name:
                    add_cartridge_type(conn, new_name, new_full_gas_mass, new_empty_mass, new_color, new_butane, new_propane)
                    st.success("Nouveau type ajouté!")
                else:
                    st.error("Veuillez entrer un nom pour le type de cartouche.")
        
        # Formulaire de modification
        st.subheader("Modifier un type existant")
        df_types = get_cartridge_types(conn)  # rafraîchir la liste
        if not df_types.empty:
            selected_type_id = st.selectbox("Sélectionnez le type à modifier", df_types['id'])
            selected_type = df_types[df_types['id'] == selected_type_id].iloc[0]
            
            with st.form("modif_type"):
                mod_name = st.text_input("Nom du type", value=selected_type['name'])
                mod_full_gas_mass = st.number_input("Masse de gaz pleine (g)", min_value=0.0, 
                                                    value=float(selected_type['full_gas_mass']), format="%.2f")
                mod_empty_mass = st.number_input("Masse du contenant vide (g)", min_value=0.0, 
                                                 value=float(selected_type['empty_mass']), format="%.2f")
                mod_color = st.selectbox("Couleur", ["Bleu", "Rouge"], 
                                         index=0 if selected_type['color'] == "Bleu" else 1)
                mod_butane = st.number_input("Pourcentage de Butane", min_value=0.0, max_value=1.0, 
                                             value=float(selected_type['butane']), format="%.2f")
                mod_propane = st.number_input("Pourcentage de Propane", min_value=0.0, max_value=1.0, 
                                              value=float(selected_type['propane']), format="%.2f")
                
                mod_submitted = st.form_submit_button("Mettre à jour")
                if mod_submitted:
                    update_cartridge_type(conn, selected_type_id, mod_name, mod_full_gas_mass, 
                                          mod_empty_mass, mod_color, mod_butane, mod_propane)
                    st.success("Type mis à jour!")

        st.subheader("Supprimer un type existant")
        df_types_delete = get_cartridge_types(conn)  # pour avoir la liste à jour

        if not df_types_delete.empty:
            delete_id = st.selectbox(
                "Sélectionnez le type à supprimer", 
                df_types_delete['id'], 
                format_func=lambda x: df_types_delete.loc[df_types_delete['id']==x, 'name'].values[0]
            )
            if st.button("Supprimer ce type"):
                delete_cartridge_type(conn, delete_id)
                st.success("Type supprimé avec succès!")
                st.experimental_rerun()

    
    elif menu == "Historique":
        st.header("Historique des Transactions")
        
        # Afficher l'historique
        df_transactions = get_transactions(conn)
        st.dataframe(df_transactions, use_container_width=True)

        
        # Modification / Suppression d'une transaction
        st.subheader("Modifier ou Supprimer une transaction")
        if not df_transactions.empty:
            transaction_ids = df_transactions['ID'].tolist()
            selected_trans_id = st.selectbox("Sélectionnez l'ID de la transaction", transaction_ids)
            selected_trans = df_transactions[df_transactions['ID'] == selected_trans_id].iloc[0]
            
            st.write("**Transaction sélectionnée :**")
            st.write(selected_trans)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Supprimer la transaction"):
                    delete_transaction(conn, selected_trans_id)
                    st.success("Transaction supprimée.")
                    st.experimental_rerun()
            
            with col2:
                # Formulaire de modification
                with st.expander("Modifier la transaction"):
                    with st.form("edit_transaction"):
                        new_date = st.text_input("Date", value=selected_trans['Date'])
                        new_measured_weight = st.number_input("Poids mesuré (g)", 
                                                              value=float(selected_trans['Poids mesuré (g)']))
                        new_gas_mass = st.number_input("Masse de gaz (g)", 
                                                       value=float(selected_trans['Masse de gaz (g)']))
                        new_missing_gas = st.number_input("Gaz manquant (g)", 
                                                          value=float(selected_trans['Gaz manquant (g)']))
                        new_butane_to_add = st.number_input("Butane à ajouter (g)", 
                                                            value=float(selected_trans['Butane à ajouter (g)']))
                        new_propane_to_add = st.number_input("Propane à ajouter (g)", 
                                                             value=float(selected_trans['Propane à ajouter (g)']))
                        new_client_name = st.text_input("Nom du client", value=selected_trans['Nom du client'] or "")
                        
                        submitted_edit = st.form_submit_button("Enregistrer les modifications")
                        if submitted_edit:
                            update_transaction(conn, selected_trans_id, new_date, new_measured_weight, 
                                               new_gas_mass, new_missing_gas, new_butane_to_add, 
                                               new_propane_to_add, new_client_name)
                            st.success("Transaction mise à jour!")
                            st.experimental_rerun()

if __name__ == '__main__':
    main()
