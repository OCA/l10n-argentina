##############################################################################
#
# Amount To Text - Sp (Open UnIT)
# (Este Archivo va en la carpeta /bin/tools)
#
##############################################################################

import math

#-------------------------------------------------------------
# Spanish
#-------------------------------------------------------------

unites = {
	0: ' ', 1:'un', 2:'dos', 3:'tres', 4:'cuatro', 5:'cinco', 6:'seis', 7:'siete', 8:'ocho', 9:'nueve', 10:'diez',
	11:'once', 12:'doce', 13:'trece', 14:'catorce', 15:'quince', 16:'dieciseis', 17:'diecisiete', 18:'dieciocho', 19:'diecinueve', 20:'veinte',
	21:'veintiuno', 22:'veintidos', 23:'veintitres', 24:'veinticuatro', 25:'veinticinco', 26:'veintiseis', 27:'veintisiete', 28:'veintiocho', 29:'veintinueve'}

dizaine = {
	1: 'diez', 2:'veinte', 3:'treinta',4:'cuarenta', 5:'cincuenta', 6:'sesenta', 7:'setenta', 8:'ochenta', 9:'noventa'
}

centaine = {
	0:'', 1: 'ciento', 2:'doscientos', 3:'trescientos',4:'cuatrocientos', 5:'quinientos', 6:'seiscientos', 7:'setecientos', 8:'ochocientos', 9:'novecientos'
}

mille = {
	0:' ', 1:'mil'
}

def _100_to_text_sp(chiffre):
	if chiffre in unites:
		return unites[chiffre]
	else:
		if chiffre%10>0:
			return dizaine[chiffre / 10]+' y '+unites[chiffre % 10]
		else:
			return dizaine[chiffre / 10]

def _1000_to_text_sp(chiffre):
	d = _100_to_text_sp(chiffre % 100)
	d2 = chiffre/100
	if d2>0 and d:
		return centaine[d2]+' '+d
	elif d2>0 and not(d):
			return 'cien'
	elif d2>1 and not(d):
		return centaine[d2]+'s'
	else:
			return centaine[d2] or d

def _10000_to_text_sp(chiffre):
	if chiffre==0:
		return 'cero'
	part1 = _1000_to_text_sp(chiffre % 1000)
	part2 = mille.get(chiffre / 1000,  _1000_to_text_sp(chiffre / 1000)+' mil')
	if part2 and part1:
		part1 = ' '+part1
	return part2+part1

def amount_to_text_sp(number, currency):
	#~ return ''
	units_number = int(number)
	units_name = currency
	if units_number > 1:
		units_name += 's'
	units = _10000_to_text_sp(units_number)
	units = units_number and '%s %s' % (units, units_name) or ''

#	cents_number = int(number * 100) % 100
	cents_number = int(round(math.fmod(number * 100,100)))
	cents_name = (cents_number > 1) and 'centavos' or 'centavo'
	cents = _100_to_text_sp(cents_number)
	cents = cents_number and '%s %s' % (cents, cents_name) or ''

#	cents = '%s / 100' % (cents_number)

	if units and cents:
		cents = ' '+cents

	return (cents_number > 1) and (units + ' con ' + cents) or units

