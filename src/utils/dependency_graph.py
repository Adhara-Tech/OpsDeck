def get_full_dependency_tree(root_service, direction='upstream', visited=None, edges=None):
    """
    Recorre recursivamente las dependencias.
    direction: 'upstream' (de qué dependo) o 'downstream' (quién depende de mí).
    """
    if visited is None: visited = set()
    if edges is None: edges = []

    # Evitamos procesar el mismo nodo raíz múltiples veces en la misma llamada raíz, 
    # pero necesitamos permitir que sea visitado como hijo.
    # El set 'visited' rastrea nodos ya expandidos para evitar ciclos.
    
    visited.add(root_service.id)
    
    # Seleccionar dirección
    if direction == 'upstream':
        relatives = root_service.upstream_dependencies
    else: # downstream
        relatives = root_service.downstream_dependencies
    
    for related_service in relatives:
        # Guardar la arista: (Origen, Destino)
        # Always store logical flow: Dependency -> Service (Upstream) or Service -> Dependent (Downstream)
        # But for 'upstream', the related_service IS the parent. 
        # So: related_service -> root_service
        
        if direction == 'upstream':
             edges.append({
                'from': related_service.id, 
                'from_name': related_service.name,
                'to': root_service.id,
                'to_name': root_service.name
            })
        else: # downstream
             edges.append({
                'from': root_service.id, 
                'from_name': root_service.name,
                'to': related_service.id,
                'to_name': related_service.name
            })
        
        if related_service.id not in visited:
            get_full_dependency_tree(related_service, direction, visited, edges)
            
    return edges
