"""Helper functions to query info and elements from Revit."""

from collections import namedtuple

from pyrevit import HOST_APP, PyRevitException
from pyrevit import framework
from pyrevit.compat import safe_strtype
from pyrevit import DB
from pyrevit.revit import db


GRAPHICAL_VIEWTYPES = [
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.Elevation,
    DB.ViewType.ThreeD,
    DB.ViewType.Schedule,
    DB.ViewType.DrawingSheet,
    DB.ViewType.Report,
    DB.ViewType.DraftingView,
    DB.ViewType.Legend,
    DB.ViewType.EngineeringPlan,
    DB.ViewType.AreaPlan,
    DB.ViewType.Section,
    DB.ViewType.Detail,
    DB.ViewType.CostReport,
    DB.ViewType.LoadsReport,
    DB.ViewType.PresureLossReport,
    DB.ViewType.ColumnSchedule,
    DB.ViewType.PanelSchedule,
    DB.ViewType.Walkthrough,
    DB.ViewType.Rendering
    ]


GridPoint = namedtuple('GridPoint', ['point', 'grids'])


def get_biparam_stringequals_filter(bip_paramvalue_dict):
    filters = []
    for bip, fvalue in bip_paramvalue_dict.items():
        bip_id = DB.ElementId(bip)
        bip_valueprovider = DB.ParameterValueProvider(bip_id)
        bip_valuerule = DB.FilterStringRule(bip_valueprovider,
                                            DB.FilterStringEquals(),
                                            fvalue,
                                            True)
        filters.append(bip_valuerule)

    if filters:
        return DB.ElementParameterFilter(
            framework.List[DB.FilterRule](filters)
            )
    else:
        raise PyRevitException('Error creating filters.')


def get_all_elements(doc=None):
    return DB.FilteredElementCollector(doc or HOST_APP.doc)\
             .WhereElementIsNotElementType()\
             .ToElements()


def get_param_value(targetparam):
    if targetparam.StorageType == DB.StorageType.Double:
        value = targetparam.AsDouble()
    elif targetparam.StorageType == DB.StorageType.Integer:
        value = targetparam.AsInteger()
    elif targetparam.StorageType == DB.StorageType.String:
        value = targetparam.AsString()
    elif targetparam.StorageType == DB.StorageType.ElementId:
        value = targetparam.AsElementId()

    return value


def get_value_range(param_name, doc=None):
    values = set()
    for el in get_all_elements(doc):
        targetparam = el.LookupParameter(param_name)
        if targetparam:
            value = get_param_value(targetparam)
            if value is not None \
                    and safe_strtype(value).lower() != 'none':
                if type(value) == str \
                        and not value.isspace():
                    values.add(value)
                else:
                    values.add(value)
    return values


def get_elements_by_parameter(param_name, param_value,
                              doc=None, partial=False):
    # does not work in < 2016
    # spid = framework.Guid('24353a46-1313-46a4-a779-d33ffe9353ab')
    # pid = DB.SharedParameterElement.Lookup(revit.doc, spid)
    # pp = DB.ParameterValueProvider(pid)
    # pe = DB.FilterStringEquals()
    # vrule = DB.FilterDoubleRule(pp, pe, scope_id, True)
    # param_filter = DB.ElementParameterFilter(vrule)
    # elements = DB.FilteredElementCollector(revit.doc) \
    #           .WherePasses(param_filter) \
    #           .ToElementIds()

    found_els = []
    for el in get_all_elements(doc):
        targetparam = el.LookupParameter(param_name)
        if targetparam:
            value = get_param_value(targetparam)
            if partial \
                    and value is not None \
                    and type(value) == str \
                    and param_value in value:
                found_els.append(el)
            elif param_value == value:
                found_els.append(el)
    return found_els


def get_elements_by_shared_parameter(param_name, param_value,
                                     inverse=False, doc=None):
    doc = doc or HOST_APP.doc
    param_id = get_sharedparam_id(param_name)
    if param_id:
        pp = DB.ParameterValueProvider(param_id)
        pe = DB.FilterStringEquals()
        vrule = DB.FilterStringRule(pp, pe, param_value, True)
        if inverse:
            vrule = DB.FilterInverseRule(vrule)
        param_filter = DB.ElementParameterFilter(vrule)
        return DB.FilteredElementCollector(doc)\
                 .WherePasses(param_filter)\
                 .ToElements()


def get_elements_by_category(element_bicats, elements=None, doc=None):
    # if source elements is provided
    if elements:
        return [x for x in elements
                if get_builtincategory(x.Category.Name)
                in element_bicats]

    # otherwise collect from model
    cat_filters = [DB.ElementCategoryFilter(x) for x in element_bicats]
    elcats_filter = \
        DB.LogicalOrFilter(framework.List[DB.ElementFilter](cat_filters))
    return DB.FilteredElementCollector(doc or HOST_APP.doc)\
             .WherePasses(elcats_filter)\
             .WhereElementIsNotElementType()\
             .ToElements()


def get_family(family_name, doc=None):
    famsyms = \
        DB.FilteredElementCollector(doc or HOST_APP.doc)\
          .WherePasses(
              get_biparam_stringequals_filter(
                  {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name}
                  )
              )\
          .WhereElementIsElementType()\
          .ToElements()
    return famsyms


def get_elements_by_family(family_name, doc=None):
    famsyms = \
        DB.FilteredElementCollector(doc or HOST_APP.doc)\
          .WherePasses(
              get_biparam_stringequals_filter(
                  {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name}
                  )
              )\
          .WhereElementIsNotElementType()\
          .ToElements()
    return famsyms


def get_elements_by_familytype(family_name, symbol_name, doc=None):
    syms = \
        DB.FilteredElementCollector(doc or HOST_APP.doc)\
          .WherePasses(
              get_biparam_stringequals_filter(
                  {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name,
                   DB.BuiltInParameter.SYMBOL_NAME_PARAM: symbol_name
                   }
                  )
              )\
          .WhereElementIsNotElementType()\
          .ToElements()
    return syms


def find_workset(workset_name_or_list, doc=None, partial=True):
    workset_clctr = \
        DB.FilteredWorksetCollector(doc or HOST_APP.doc).ToWorksets()
    if type(workset_name_or_list) == list:
        for workset in workset_clctr:
            for workset_name in workset_name_or_list:
                if workset_name in workset.Name:
                    return workset

    elif type(workset_name_or_list) == str:
        workset_name = workset_name_or_list

        if partial:
            for workset in workset_clctr:
                if workset_name in workset.Name:
                    return workset
        else:
            for workset in workset_clctr:
                if workset_name == workset.Name:
                    return workset


def model_has_family(family_name, doc=None):
    collector = get_family(family_name, doc=doc)
    return hasattr(collector, 'Count') and collector.Count > 0


def model_has_workset(workset_name, partial=False, doc=None):
    return find_workset(workset_name, partial=partial, doc=doc)


def get_sharedparam_definition_file():
    if HOST_APP.app.SharedParametersFilename:
        sparamf = HOST_APP.app.OpenSharedParameterFile()
        if sparamf:
            return sparamf
        else:
            raise PyRevitException('Failed opening Shared Parameters file.')
    else:
        raise PyRevitException('No Shared Parameters file defined.')


def get_defined_sharedparams():
    msp_list = []
    for def_group in get_sharedparam_definition_file().Groups:
        msp_list.extend([db.ModelSharedParam(x)
                         for x in def_group.Definitions])
    return msp_list


def get_model_sharedparams(doc=None):
    doc = doc or HOST_APP.doc
    param_bindings = doc.ParameterBindings
    pb_iterator = param_bindings.ForwardIterator()
    pb_iterator.Reset()

    msp_list = []
    while pb_iterator.MoveNext():
        msp = db.ModelSharedParam(pb_iterator.Key,
                                  param_bindings[pb_iterator.Key])
        msp_list.append(msp)

    return msp_list


def get_sharedparam_id(param_name):
    for sp in get_model_sharedparams():
        if sp.name == param_name:
            return sp.param_def.Id


def get_model_sharedparam(param_id_or_name, doc=None):
    msp_list = get_model_sharedparams(doc or HOST_APP.doc)
    for x in msp_list:
        if x == param_id_or_name:
            return x


def model_has_sharedparam(param_id_or_name, doc=None):
    return get_model_sharedparam(param_id_or_name, doc=doc)


def get_project_info():
    return db.CurrentProjectInfo()


def get_revisions(doc=None):
    return list(DB.FilteredElementCollector(doc or HOST_APP.doc)
                  .OfCategory(DB.BuiltInCategory.OST_Revisions)
                  .WhereElementIsNotElementType())


def get_sheet_revisions(sheet, doc=None):
    doc = doc or HOST_APP.doc
    return [doc.GetElement(x) for x in sheet.GetAdditionalRevisionIds()]


def get_sheets(include_placeholders=True, doc=None):
    sheets = list(DB.FilteredElementCollector(doc or HOST_APP.doc)
                  .OfCategory(DB.BuiltInCategory.OST_Sheets)
                  .WhereElementIsNotElementType())
    if not include_placeholders:
        return [x for x in sheets if not x.IsPlaceholder]

    return sheets


def get_links(linktype=None, doc=None):
    doc = doc or HOST_APP.doc

    location = doc.PathName
    if not location:
        raise PyRevitException('PathName is empty. Model is not saved.')

    links = []
    modelPath = \
        DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    if not modelPath:
        raise PyRevitException('Model is not saved. Can not read links.')
    try:
        transData = DB.TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            link = doc.GetElement(refId)
            if linktype:
                if extRef.ExternalFileReferenceType == linktype:
                    links.append(db.ExternalRef(link, extRef))
            else:
                links.append(db.ExternalRef(link, extRef))
        return links
    except Exception as e:
        raise PyRevitException('Error reading links from model path: {} | {}'
                               .format(modelPath, e))


def get_linked_models(doc=None, loaded_only=False):
    doc = doc or HOST_APP.doc
    linkedmodels = get_links(linktype=DB.ExternalFileReferenceType.RevitLink,
                             doc=doc)
    if loaded_only:
        return [x for x in linkedmodels
                if DB.RevitLinkType.IsLoaded(doc, x.id)]

    return linkedmodels


def get_linked_model_doc(linked_model):
    lmodel = None
    if isinstance(linked_model, DB.RevitLinkType):
        lmodel = db.ExternalRef(linked_model)
    elif isinstance(linked_model, db.ExternalRef):
        lmodel = linked_model

    if lmodel:
        for open_doc in HOST_APP.docs:
            if open_doc.Title == lmodel.name:
                return open_doc


def find_first_legend(doc=None):
    doc = doc or HOST_APP.doc
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if v.ViewType == DB.ViewType.Legend:
            return v
    return None


def compare_revisions(src_rev, dest_rev, case_sensitive=False):
    return all(db.BaseWrapper.compare_attrs(src_rev, dest_rev,
                                            ['RevisionDate',
                                             'Description',
                                             'IssuedBy',
                                             'IssuedTo'],
                                            case_sensitive=case_sensitive))


def get_all_views(doc=None, include_nongraphical=False):
    doc = doc or HOST_APP.doc
    all_views = DB.FilteredElementCollector(doc) \
                  .OfClass(DB.View) \
                  .WhereElementIsNotElementType() \
                  .ToElements()

    if not include_nongraphical:
        return [x for x in all_views
                if x.ViewType in GRAPHICAL_VIEWTYPES
                and not x.IsTemplate
                and not x.ViewSpecific]

    return all_views


def get_all_schedules(doc=None):
    doc = doc or HOST_APP.doc
    all_scheds = DB.FilteredElementCollector(doc) \
                   .OfClass(DB.ViewSchedule) \
                   .WhereElementIsNotElementType() \
                   .ToElements()
    return all_scheds


def get_view_by_name(view_name, doc=None):
    doc = doc or HOST_APP.doc
    for view in get_all_views(doc=doc):
        if view.ViewName == view_name:
            return view


def get_schedules_on_sheet(viewsheet, doc=None):
    doc = doc or HOST_APP.doc
    all_sheeted_scheds = DB.FilteredElementCollector(doc)\
                           .OfClass(DB.ScheduleSheetInstance)\
                           .ToElements()
    return [x for x in all_sheeted_scheds
            if x.OwnerViewId == viewsheet.Id
            and not doc.GetElement(x.ScheduleId).IsTitleblockRevisionSchedule]


def is_sheet_empty(viewsheet):
    sheet_views = viewsheet.GetAllViewports()
    sheet_scheds = get_schedules_on_sheet(viewsheet, doc=viewsheet.Document)
    if sheet_views or sheet_scheds:
        return False
    return True


def get_doc_categories(doc=None):
    doc = doc or HOST_APP.doc
    all_cats = []
    cats = doc.Settings.Categories
    all_cats.extend(cats)
    for cat in cats:
        all_cats.extend([x for x in cat.SubCategories])
    return all_cats


def get_category(cat_name_or_builtin, doc=None):
    doc = doc or HOST_APP.doc
    all_cats = get_doc_categories()
    if isinstance(cat_name_or_builtin, str):
        for cat in all_cats:
            if cat.Name == cat_name_or_builtin:
                return cat
    elif isinstance(cat_name_or_builtin, DB.BuiltInCategory):
        for cat in all_cats:
            if cat.Id.IntegerValue == int(cat_name_or_builtin):
                return cat
    elif isinstance(cat_name_or_builtin, DB.Category):
        return cat_name_or_builtin


def get_builtincategory(cat_name_or_id, doc=None):
    doc = doc or HOST_APP.doc
    cat_id = None
    if isinstance(cat_name_or_id, str):
        cat = get_category(cat_name_or_id)
        if cat:
            cat_id = cat.Id.IntegerValue
    elif isinstance(cat_name_or_id, DB.ElementId):
        cat_id = cat_name_or_id.IntegerValue
    if cat_id:
        for bicat in DB.BuiltInCategory.GetValues(DB.BuiltInCategory):
            if int(bicat) == cat_id:
                return bicat


def get_view_cutplane_offset(view):
    viewrange = view.GetViewRange()
    return viewrange.GetOffset(DB.PlanViewPlane.CutPlane)


def get_project_location_transform(doc=None):
    doc = doc or HOST_APP.doc
    return doc.ActiveProjectLocation.GetTransform()


def get_all_linkedmodels(doc=None):
    doc = doc or HOST_APP.doc
    return DB.FilteredElementCollector(doc)\
             .OfClass(DB.RevitLinkType)\
             .ToElements()


def get_all_linkeddocs(doc=None):
    doc = doc or HOST_APP.doc
    linkinstances = DB.FilteredElementCollector(doc)\
                      .OfClass(DB.RevitLinkInstance)\
                      .ToElements()
    return {x.GetLinkDocument() for x in linkinstances}


def get_all_grids(group_by_direction=False,
                  include_linked_models=False, doc=None):
    doc = doc or HOST_APP.doc
    target_docs = [doc]
    if include_linked_models:
        target_docs.extend(get_all_linkeddocs())

    all_grids = []
    for tdoc in target_docs:
        if tdoc is not None:
            all_grids.extend(list(
                DB.FilteredElementCollector(tdoc)
                  .OfCategory(DB.BuiltInCategory.OST_Grids)
                  .WhereElementIsNotElementType()
                  .ToElements()
                  ))

    if group_by_direction:
        direcs = {db.XYZPoint(x.Curve.Direction) for x in all_grids}
        grouped_grids = dict()
        for direc in direcs:
            grouped_grids[direc] = [x for x in all_grids
                                    if direc == db.XYZPoint(x.Curve.Direction)]
        return grouped_grids
    return all_grids


def get_gridpoints(grids=None, include_linked_models=False, doc=None):
    doc = doc or HOST_APP.doc
    source_grids = grids or get_all_grids(
        doc=doc,
        include_linked_models=include_linked_models
        )
    gints = dict()
    for grid1 in source_grids:
        for grid2 in source_grids:
            results = framework.clr.Reference[DB.IntersectionResultArray]()
            intres = grid1.Curve.Intersect(grid2.Curve, results)
            if intres == DB.SetComparisonResult.Overlap:
                gints[db.XYZPoint(results.get_Item(0).XYZPoint)] = \
                    [grid1, grid2]
    return [GridPoint(point=k, grids=v) for k, v in gints.items()]


def get_closest_gridpoint(element, gridpoints):
    dist = (gridpoints[0].point.unwrap().DistanceTo(element.Location.Point),
            gridpoints[0])
    for gp in gridpoints:
        d = gp.point.unwrap().DistanceTo(element.Location.Point)
        if d < dist[0]:
            dist = (d, gp)
    return dist[1]


def get_category_set(category_list, doc=None):
    doc = doc or HOST_APP.doc
    cat_set = HOST_APP.app.Create.NewCategorySet()
    for builtin_cat in category_list:
        cat = doc.Settings.Categories.get_Item(builtin_cat)
        cat_set.Insert(cat)
    return cat_set


def get_all_category_set(bindable=True, doc=None):
    doc = doc or HOST_APP.doc
    cat_set = HOST_APP.app.Create.NewCategorySet()
    for cat in doc.Settings.Categories:
        if bindable:
            if cat.AllowsBoundParameters:
                cat_set.Insert(cat)
        else:
            cat_set.Insert(cat)
    return cat_set


def get_rule_filters(doc=None):
    doc = doc or HOST_APP.doc
    rfcl = DB.FilteredElementCollector(doc)\
             .OfClass(DB.ParameterFilterElement)\
             .WhereElementIsNotElementType()\
             .ToElements()
    return list(rfcl)


def get_connected_circuits(element, spare=False, space=False):
    circuit_types = [DB.Electrical.CircuitType.Circuit]
    if spare:
        circuit_types.append(DB.Electrical.CircuitType.Spare)
    if space:
        circuit_types.append(DB.Electrical.CircuitType.Space)

    if element.MEPModel and element.MEPModel.ElectricalSystems:
        return [x for x in element.MEPModel.ElectricalSystems
                if x.CircuitType in circuit_types]


def get_element_categories(elements):
    catsdict = {x.Category.Name: x.Category for x in elements}
    uniquenames = set(catsdict.keys())
    return [catsdict[x] for x in uniquenames]


def get_category_schedules(category_or_catname, doc=None):
    doc = doc or HOST_APP.doc
    cat = get_category(category_or_catname)
    scheds = get_all_schedules(doc=doc)
    return [x for x in scheds if x.Definition.CategoryId == cat.Id]


def get_schedule_field(schedule, field_name):
    for field_idx in schedule.Definition.GetFieldOrder():
        field = schedule.Definition.GetField(field_idx)
        if field.GetName() == field_name:
            return field


def get_schedule_filters(schedule, field_name, return_index=False):
    matching_filters = []
    field = get_schedule_field(schedule, field_name)
    if field:
        for idx, sfilter in enumerate(schedule.Definition.GetFilters()):
            if sfilter.FieldId == field.FieldId:
                if return_index:
                    matching_filters.append(idx)
                else:
                    matching_filters.append(sfilter)
    return matching_filters


def get_sheet_tblocks(src_sheet):
    sheet_tblocks = DB.FilteredElementCollector(src_sheet.Document,
                                                src_sheet.Id)\
                      .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)\
                      .WhereElementIsNotElementType()\
                      .ToElements()
    return list(sheet_tblocks)


def get_sheet_sets(doc=None):
    doc = doc or HOST_APP.doc
    viewsheetsets = DB.FilteredElementCollector(doc)\
                      .OfClass(DB.ViewSheetSet)\
                      .WhereElementIsNotElementType()\
                      .ToElements()
    return list(viewsheetsets)


def get_rev_number(revision):
    revnum = revision.SequenceNumber
    if hasattr(revision, 'RevisionNumber'):
        revnum = revision.RevisionNumber
    return revnum


def get_pointclouds(doc=None):
    doc = doc or HOST_APP.doc
    return get_elements_by_category([DB.BuiltInCategory.OST_PointClouds],
                                    doc=doc)