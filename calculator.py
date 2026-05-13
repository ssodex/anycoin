import pandas as pd
import yfinance as yf

def analyzuj_nakupy(csv_soubor):
    print("Načítám data a stahuji aktuální kurz Bitcoinu...")
    
    # Načtení dat z CSV
    try:
        df = pd.read_csv(csv_soubor)
    except FileNotFoundError:
        print(f"Chyba: Soubor {csv_soubor} nebyl nalezen.")
        return
    
    # Rozdělení na nákupy (kolik BTC přibylo) a platby (kolik CZK ubylo)
    fills = df[df['Type'] == 'trade fill'].copy()
    payments = df[df['Type'] == 'trade payment'].copy()
    refunds = df[df['Type'] == 'trade refund'].copy()
    
    # Seskupení podle Order ID
    btc_nakoupeno = fills.groupby('Order ID')['Amount'].sum().reset_index().rename(columns={'Amount': 'BTC'})
    czk_zaplaceno = payments.groupby('Order ID')['Amount'].sum().reset_index().rename(columns={'Amount': 'CZK_Spent'})
    czk_refund = refunds.groupby('Order ID')['Amount'].sum().reset_index().rename(columns={'Amount': 'CZK_Refund'})
    
    # Platby jsou záporné hodnoty, proto je převedeme na kladné
    czk_zaplaceno['CZK_Spent'] = -czk_zaplaceno['CZK_Spent']
    
    # Spojení tabulek podle Order ID
    nakupy = pd.merge(btc_nakoupeno, czk_zaplaceno, on='Order ID', how='left')
    nakupy = pd.merge(nakupy, czk_refund, on='Order ID', how='left').fillna(0)
    
    # Odečtení případných refundací (vrácení peněz)
    nakupy['CZK'] = nakupy['CZK_Spent'] - nakupy['CZK_Refund']
    
    # Přiřazení data z 'trade fill' (stačí nám první unikátní datum pro dané Order ID)
    daty = fills.drop_duplicates('Order ID')[['Order ID', 'Date']]
    nakupy = pd.merge(nakupy, daty, on='Order ID', how='left')
    nakupy['Date'] = pd.to_datetime(nakupy['Date']).dt.strftime('%d.%m.%Y')
    
    # --- OPRAVENÉ STAHOVÁNÍ CENY ---
    try:
        # Nejdříve získáme spolehlivou cenu BTC v dolarech
        btc_usd = yf.Ticker("BTC-USD")
        cena_btc_usd = btc_usd.history(period="1d")['Close'].iloc[-1]
        
        # Poté získáme aktuální kurz Dolaru vůči Koruně (USD/CZK)
        usd_czk = yf.Ticker("CZK=X")
        kurz_usd_czk = usd_czk.history(period="1d")['Close'].iloc[-1]
        
        # Vynásobením získáme aktuální cenu BTC v CZK
        aktualni_cena_czk = cena_btc_usd * kurz_usd_czk
    except Exception as e:
        print(f"Chyba při stahování ceny z internetu: {e}")
        return

    # Výpočty pro každý nákup
    nakupy['Aktualni_hodnota'] = nakupy['BTC'] * aktualni_cena_czk
    nakupy['Zisk'] = nakupy['Aktualni_hodnota'] - nakupy['CZK']
    
    # Výpočty pro celková čísla
    celkem_btc = nakupy['BTC'].sum()
    celkem_investovano = nakupy['CZK'].sum()
    celkova_hodnota = celkem_btc * aktualni_cena_czk
    celkovy_zisk = celkova_hodnota - celkem_investovano
    
    # --- Výpis ---
    print("\n" + "="*50)
    print("CELKOVÉ SHRNUTÍ")
    print("="*50)
    print(f"Celkem investováno:  {celkem_investovano:,.2f} CZK".replace(',', ' '))
    print(f"Získáno BTC:         {celkem_btc:.6f} BTC")
    print(f"Aktuální hodnota:    {celkova_hodnota:,.2f} CZK".replace(',', ' '))
    print(f"CELKOVÝ ZISK:        {celkovy_zisk:,.2f} CZK".replace(',', ' '))
    
    print("\n" + "="*80)
    print(f"{'Datum':<12} | {'Nakoupeno BTC':<15} | {'Investice CZK':<15} | {'Aktuální C.':<15} | {'Zisk CZK':<15}")
    print("-" * 80)
    
    for index, row in nakupy.iterrows():
        zisk_znaménko = "+" if row['Zisk'] > 0 else ""
        print(f"{row['Date']:<12} | {row['BTC']:<15.6f} | {row['CZK']:<15.2f} | {row['Aktualni_hodnota']:<15.2f} | {zisk_znaménko}{row['Zisk']:.2f}")

if __name__ == "__main__":
    # Ujisti se, že tady je správný název tvého souboru
    analyzuj_nakupy('transactions-2.csv')