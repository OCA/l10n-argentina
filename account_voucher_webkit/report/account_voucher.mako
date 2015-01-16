<html>
<head>
     <style type="text/css">
                ${css}
            </style>
</head>
<body>
    <%!
    def _get_line_name(l):
        if not l.invoice_id.id:
            return l.ref

        elif l.invoice_id:
            invoice = l.invoice_id
            type = ''
            if invoice.type == 'in_invoice':
                if invoice.is_debit_note:
                    type = 'ND'
                else:
                    type = 'FAC'
            elif invoice.type == 'in_refund':
                type = 'NC'
            elif invoice.type == 'out_refund':
                type = 'NC'
            elif invoice.type == 'out_invoice':
                if invoice.is_debit_note:
                    type = 'ND'
                else:
                    type = 'FAC'

            return type + ' ' + ((invoice.denomination_id and invoice.denomination_id.name) or '') + invoice.internal_number

        return l.ref
    %>
    %for o in objects:
    <% setLang(o.partner_id.lang) %>
		<table width="100%">
			<tr>
        		<td align="right" style="font-size:12px;">
                    <h1><b>X</b></h1>
          		</td>
        		<td align="right" style="font-size:12px;">
                    COMPROBANTE NO VALIDO COMO FACTURA</br>
                    ESTE 
                    %if o.type == 'payment':
						EGRESO DE CAJA  
					%endif
					%if o.type == 'receipt':
						RECIBO 
                    %endif
                    CARECE DE VALIDEZ SI NO</br>
                    SE ENCUENTRA DEBIDAMENTE FIRMADO</br>
          		</td>
             </tr>
        	<tr>
        		<td colspan="2" width="50%" align="center">
                    %if o.type == 'payment':
						<h1><b>EGRESO DE CAJA  ${ (o.number) or ''}</b></h1>
					%endif
					%if o.type == 'receipt':
						<h1><b>RECIBO OFICIAL NRO.  ${ (o.ref) or ''}</b></h1>
					%endif
          		</td>
            </tr>
        	<tr>
        		<td colspan="2" align="right" style="font-size:12px;">
                    Fecha: ${ formatLang( o.date, date=True)}
          		</td>
             </tr>
		</table>
		<table class="shipping_address" width="100%">
        	<tr>
        		<td colspan="2">
                    <h1><b>${_("Encabezado")}</b></h1>
          		</td>
             </tr>
        	<tr>
        		<td>
                    ${_("Empresa : ")} ${ o.partner_id.name or ''|entity}
          		</td>
        		<td>
                    ${_("CUIT : ")} ${ o.partner_id.vat or ''|entity}
          		</td>
             </tr>
        	<tr>
        		<td colspan="2">
                    ${_("Ref : ")} ${ o.partner_id.ref or ''|entity}
          		</td>
             </tr>
        	<tr>
        		<td colspan="2">
                    %if o.type == 'receipt':
                    Recibimos de ${ o.partner_id.name or ''|entity} la cantidad de 
                    ${ amount_to_text_sp(o.amount, 'peso')} cuyo importe una vez hecho efectivo sera acreditado en su cuenta segun 
                    detalle / al pie de este recibo.
                    %endif
                    %if o.type == 'payment':
						La cantidad de ${ amount_to_text_sp(o.amount, 'peso')}
					%endif
          		</td>
             </tr>
		</table>
		<h1><b>Comprobantes cancelados</b></h1>
		<table width="100%" class="basic_table">
        	<tr>
        		<td width="48%" class="title">
                    ${_("Comprobante")}
          		</td>
<!--
        		<td width="26%" class="title">
                    ${_("Asiento")}
          		</td>
-->
        		<td width="10%" class="title">
                    ${_("Fecha")}
          		</td>
        		<td width="14%" class="title">
                    ${_("Cantidad original")}
          		</td>
        		<td width="12%" class="title">
                    ${_("Saldo")}
          		</td>
        		<td width="16%" class="title">
                    ${_("Neto a cobrar")}
          		</td>
<!--
        		<td width="8%" class="title">
                    ${_("Conciliado")}
          		</td>
-->
             </tr>
		</table>
		%if o.type == 'payment':
			%if o.line_dr_ids:
				%for line in o.line_dr_ids:
					<table class="shipping_address" width="100%">
					<tr>
						<td width="48%" align="left" style="border-bottom:1px solid lightGrey;">
							${ _get_line_name(line) or '' | entity}
						</td>
<!--
						<td width="26%" style="border-bottom:1px solid lightGrey;">
							${ line.name or '' | entity}
						</td>
-->
						<td width="10%" align="center" style="border-bottom:1px solid lightGrey;">
							${ line.date_original or '' | entity}
						</td>
						<td width="14%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount_original or '' | entity}
						</td>
						<td width="12%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ saldo(line.amount_original, line.amount)}
						</td>
						<td width="16%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount or '' | entity}
						</td>
<!--
						<td width="8%" align="right" style="border-bottom:1px solid lightGrey;">
							%if line.reconcile is True:
								<b>Verdadero</b>
							%else:
								<b>Falso</b>
							%endif
						</td>
-->
					 </tr>
				</table>
				%endfor
				<table class="shipping_address" width="100%">
					<tr>
						<td colspan="6" align="right">
							${_("Total")} $ ${ show_comprobantes_dr(user.id, o.id)}
						</td>
					 </tr>
				</table>
			%endif
		%else:
			%if o.line_cr_ids:
				%for line in o.line_cr_ids:
					<table class="shipping_address" width="100%">
					<tr>
						<td width="48%" align="left" style="border-bottom:1px solid lightGrey;">
							${ _get_line_name(line) or '' | entity}
						</td>
<!--
						<td width="26%" style="border-bottom:1px solid lightGrey;">
							${ line.name or '' | entity}
						</td>
-->
						<td width="10%" align="center" style="border-bottom:1px solid lightGrey;">
							${ line.date_original or '' | entity}
						</td>
						<td width="14%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount_original or '' | entity}
						</td>
						<td width="12%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ saldo(line.amount_original, line.amount)}
						</td>
						<td width="16%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount or '' | entity}
						</td>
<!--
						<td width="8%" align="right" style="border-bottom:1px solid lightGrey;">
							%if line.reconcile is True:
								<b>Verdadero</b>
							%else:
								<b>Falso</b>
							%endif
						</td>
-->
					 </tr>
				</table>
				%endfor
				<table class="shipping_address" width="100%">
					<tr>
						<td colspan="6" align="right">
							${_("Total")} $ ${ show_comprobantes_cr(user.id, o.id)}
						</td>
					 </tr>
				</table>
			%endif
		%endif
			

		<h1><b>Detalle de creditos</b></h1>
		<table width="100%" class="basic_table">
        	<tr>
        		<td width="48%" class="title">
                    ${_("Comprobante")}
          		</td>
<!--
        		<td width="26%" class="title">
                    ${_("Asiento")}
          		</td>
-->
        		<td width="10%" class="title">
                    ${_("Fecha")}
          		</td>
        		<td width="14%" class="title">
                    ${_("Cantidad original")}
          		</td>
        		<td width="12%" class="title">
                    ${_("Saldo")}
          		</td>
        		<td width="16%" class="title">
                    ${_("Neto a cobrar")}
          		</td>
<!--
        		<td width="8%" class="title">
                    ${_("Conciliado")}
          		</td>
-->
             </tr>
		</table>
		%if o.type == 'payment':
			%if o.line_cr_ids:
				%for line_cr in o.line_cr_ids:
				<table class="shipping_address" width="100%">
					<tr>
						<td width="48%" align="left" style="border-bottom:1px solid lightGrey;">
							${ _get_line_name(line_cr) or '' | entity}
						</td>
<!--
						<td width="26%" style="border-bottom:1px solid lightGrey;">
							${ line_cr.name or '' | entity}
						</td>
-->
						<td width="10%" align="center" style="border-bottom:1px solid lightGrey;">
							${ line_cr.date_original or '' | entity}
						</td>
						<td width="14%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line_cr.amount_original or '' | entity}
						</td>
						<td width="12%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ saldo(line.amount_original, line.amount)}
						</td>
						<td width="16%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line_cr.amount or '' | entity}
						</td>
<!--
						<td width="8%" align="right" style="border-bottom:1px solid lightGrey;">
							%if line_cr.reconcile is True:
								<b>Verdadero</b>
							%else:
								<b>Falso</b>
							%endif
						</td>
-->
					 </tr>
				</table>
				%endfor
				<table class="shipping_address" width="100%">
					<tr>
						<td colspan="6" align="right">
							${_("Total")} $ ${ show_comprobantes_cr(user.id, o.id)}
						</td>
					 </tr>
				</table>
			%endif
		%else:
			%if o.line_dr_ids:
				%for line in o.line_dr_ids:
					<table class="shipping_address" width="100%">
					<tr>
						<td width="48%" align="left" style="border-bottom:1px solid lightGrey;">
							${ _get_line_name(line) or '' | entity}
						</td>
<!--
						<td width="27%" style="border-bottom:1px solid lightGrey;">
							${ line.name or '' | entity}
						</td>
-->
						<td width="10%" align="center" style="border-bottom:1px solid lightGrey;">
							${ line.date_original or '' | entity}
						</td>
						<td width="14%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount_original or '' | entity}
						</td>
						<td width="12%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ saldo(line.amount_original, line.amount)}
						</td>
						<td width="16%" align="right" style="border-bottom:1px solid lightGrey;">$ 
							${ line.amount or '' | entity}
						</td>
<!--
						<td width="8%" align="right" style="border-bottom:1px solid lightGrey;">
							%if line.reconcile is True:
								<b>Verdadero</b>
							%else:
								<b>Falso</b>
							%endif
						</td>
-->
					 </tr>
				</table>
				%endfor
				<table class="shipping_address" width="100%">
					<tr>
						<td colspan="6" align="right">
							${_("Total")} $ ${ show_comprobantes_dr(user.id, o.id)}
						</td>
					 </tr>
				</table>
			%endif
		%endif
			
		%if o.payment_line_ids:
		<h1><b>Detalle de formas de pago</b></h1>
		<table width="100%" class="basic_table">
        	<tr>
        		<td width="60%" class="title">
                    ${_("Modo de pago")}
          		</td>
        		<td width="25%" class="title">
                    ${_("Fecha")}
          		</td>
        		<td width="15%" class="title">
                    ${_("Cantidad")}
          		</td>
             </tr>
		</table>
		%for pay_line in o.payment_line_ids:
		<table class="shipping_address" width="100%">
        	<tr>
        		<td width="60%" align="left" style="border-bottom:1px solid lightGrey;">
                    ${ pay_line.payment_mode_id.name or '' | entity}
          		</td>
        		<td width="25%" style="border-bottom:1px solid lightGrey;">
                    ${ pay_line.date or '' | entity}
          		</td>
        		<td width="15%" align="right" style="border-bottom:1px solid lightGrey;">$ 
                    ${ pay_line.amount or '' | entity}
          		</td>
             </tr>
		</table>
		%endfor
		<table class="shipping_address" width="100%">
        	<tr>
        		<td colspan="6" align="right">
                    ${_("Total")} $ ${ show_formas_de_pago(user.id, o.id)}
          		</td>
             </tr>
		</table>
		%endif
		%if o.type == 'payment':
		<h1><b>Detalle de cheques propios</b></h1>
		<table width="100%" class="basic_table">
        	<tr>
        		<td width="30%" class="title">
                    ${_("Nro. de cheque")}
          		</td>
        		<td width="20%" class="title">
                    ${_("Fecha de emision")}
          		</td>
        		<td width="20%" class="title">
                    ${_("Fecha de pago")}
          		</td>
        		<td width="15%" class="title">
                    ${_("Banco")}
          		</td>
        		<td width="15%" class="title">
                    ${_("Cantidad")}
          		</td>
             </tr>
		</table>
		%for issued_line in o.issued_check_ids:
		<table class="shipping_address" width="100%">
        	<tr>
        		<td width="30%" align="left" style="border-bottom:1px solid lightGrey;">
                    ${ issued_line.number or '' | entity}
          		</td>
        		<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
                    ${ issued_line.issue_date or '' | entity}
          		</td>
        		<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
                    ${ issued_line.payment_date or '' | entity}
          		</td>
        		<td width="15%" style="border-bottom:1px solid lightGrey;">
                    ${ issued_line.bank_id.name or '' | entity}
          		</td>
        		<td width="15%" align="right" style="border-bottom:1px solid lightGrey;">$ 
                    ${ issued_line.amount or '' | entity}
          		</td>
             </tr>
		</table>
		%endfor
		<table class="shipping_address" width="100%">
        	<tr>
        		<td colspan="6" align="right">
                    ${_("Total")} $ ${ show_cheques_propios(user.id, o.id)}
          		</td>
             </tr>
		</table>
		%endif
		%if o.type == 'receipt':
			%if o.third_check_receipt_ids:
			<h1><b>Detalle de cheques de terceros</b></h1><!--para recibo-->
			<table width="100%" class="basic_table">
				<tr>
					<td width="30%" class="title">
						${_("Nro. de cheque")}
					</td>
					<td width="20%" class="title">
						${_("Fecha de emision")}
					</td>
					<td width="20%" class="title">
						${_("Fecha de pago")}
					</td>
					<td width="15%" class="title">
						${_("Banco")}
					</td>
					<td width="15%" class="title">
						${_("Cantidad")}
					</td>
				 </tr>
			</table>
			%for issued_line in o.third_check_receipt_ids:
			<table class="shipping_address" width="100%">
				<tr>
					<td width="30%" align="left" style="border-bottom:1px solid lightGrey;">
						${ issued_line.number or '' | entity}
					</td>
					<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
						${ issued_line.issue_date or '' | entity}
					</td>
					<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
						${ issued_line.payment_date or '' | entity}
					</td>
					<td width="15%" style="border-bottom:1px solid lightGrey;">
						${ issued_line.bank_id.name or '' | entity}
					</td>
					<td width="15%" align="right" style="border-bottom:1px solid lightGrey;">$ 
						${ issued_line.amount or '' | entity}
					</td>
				 </tr>
			</table>
			%endfor
			<table class="shipping_address" width="100%">
				<tr>
					<td colspan="6" align="right">
						${_("Total")} $ ${ show_cheques_recibo_terceros(user.id, o.id)}
					</td>
				 </tr>
			</table>
			%endif
		%endif
		%if o.type == 'payment':
			%if o.third_check_ids:
			<h1><b>Detalle de cheques de terceros</b></h1>
			<table width="100%" class="basic_table">
				<tr>
					<td width="30%" class="title">
						${_("Nro. de cheque")}
					</td>
					<td width="20%" class="title">
						${_("Fecha de emision")}
					</td>
					<td width="20%" class="title">
						${_("Fecha de pago")}
					</td>
					<td width="15%" class="title">
						${_("Banco")}
					</td>
					<td width="15%" class="title">
						${_("Cantidad")}
					</td>
				 </tr>
			</table>
			%for issued_line in o.third_check_ids:
			<table class="shipping_address" width="100%">
				<tr>
					<td width="30%" align="left" style="border-bottom:1px solid lightGrey;">
						${ issued_line.number or '' | entity}
					</td>
					<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
						${ issued_line.issue_date or '' | entity}
					</td>
					<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
						${ issued_line.payment_date or '' | entity}
					</td>
					<td width="15%" style="border-bottom:1px solid lightGrey;">
						${ issued_line.bank_id.name or '' | entity}
					</td>
					<td width="15%" align="left" style="border-bottom:1px solid lightGrey;">$ 
						${ issued_line.amount or '' | entity}
					</td>
				 </tr>
			</table>
			%endfor
			<table class="shipping_address" width="100%">
				<tr>
					<td colspan="6" align="right">
						${_("Total")} $ ${ show_cheques_terceros(user.id, o.id)}
					</td>
				 </tr>
			</table>
			%endif
		%endif
		%if o.retention_ids:
			<h1><b>Retenciones</b></h1>
			<table width="100%" class="basic_table">
				<tr>
					<td width="30%" class="title">
						${_("Retencion")}
					</td>
					<td width="20%" class="title">
						${_("Fecha")}
					</td>
					<td width="20%" class="title">
						${_("Certificado Nro.")}
					</td>
					<td width="15%" class="title">
						${_("Base")}
					</td>
					<td width="15%" class="title">
						${_("Cantidad")}
					</td>
				 </tr>
			</table>
			%for reten_line in o.retention_ids:
			<table class="shipping_address" width="100%">
				<tr>
					<td width="30%" align="left" style="border-bottom:1px solid lightGrey;">
						${ reten_line.name or '' | entity}
					</td>
					<td width="20%" align="center" style="border-bottom:1px solid lightGrey;">
						${ reten_line.date or '' | entity}
					</td>
					<td width="20%" style="border-bottom:1px solid lightGrey;">
						${ reten_line.certificate_no or '' | entity}
					</td>
					<td width="15%" style="border-bottom:1px solid lightGrey;">
						${ reten_line.base or '' | entity}
					</td>
					<td width="15%" align="left" style="border-bottom:1px solid lightGrey;">$ 
						${ reten_line.amount or '' | entity}
					</td>
				 </tr>
			</table>
			%endfor
			<table class="shipping_address" width="100%">
				<tr>
					<td colspan="6" align="right">
						${_("Total")} $ ${ show_retenciones(user.id, o.id)}
					</td>
				 </tr>
			</table>
		%endif
	%endfor
</body>
</html>
